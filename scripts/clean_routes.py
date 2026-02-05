from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, trim, when, concat, lit, udf, row_number
)
from pyspark.sql.types import StringType
from pyspark.sql.window import Window
import os


# CONFIGURATION

NIGHT_FILE = 'data/extracted/night_routes.csv'
DAY_FILE = 'data/extracted/day_routes.csv'
PROCESSED_FOLDER = 'data/transformed/'


# Initialize Spark Session

def init_spark():
    """Initialize and return a Spark session"""
    spark = SparkSession.builder \
        .appName("GTFS Routes Transformation") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark


#  Title case for station names

def title_case_station(name):
    """Apply title case to station names"""
    if not name:
        return ""
    return name.strip().title()

title_case_udf = udf(title_case_station, StringType())


# FUNCTION: Clean routes DataFrame

def clean_routes(spark, df, train_type):
    """
    Cleans a routes DataFrame:
    - Strip whitespace
    - Fill missing route_name_simple
    - Deduplicate bidirectional routes
    - Normalize capitalization
    - Add 'type' column
    """
    
    print(f"   Cleaning {train_type} routes...")
    print(f"   Input records: {df.count()}")
    
    # Strip whitespace from origin and destination
    df = df.withColumn("origin", trim(col("origin")))
    df = df.withColumn("destination", trim(col("destination")))
    
    # Normalize capitalization for origin/destination (title case)
    df = df.withColumn("origin", title_case_udf(col("origin")))
    df = df.withColumn("destination", title_case_udf(col("destination")))
    
    # Fill route_name_simple if missing or empty
    df = df.withColumn(
        "route_name_simple",
        when(
            (col("route_name_simple").isNull()) | 
            (trim(col("route_name_simple")) == ""),
            concat(col("origin"), lit(" → "), col("destination"))
        ).otherwise(col("route_name_simple"))
    )
    
    # Create a sorted pair for deduplication of bidirectional routes
    df = df.withColumn(
        "route_pair",
        when(
            col("origin") < col("destination"),
            concat(col("origin"), lit("_"), col("destination"))
        ).otherwise(
            concat(col("destination"), lit("_"), col("origin"))
        )
    )
    
    # Deduplicate - keep first occurrence of each route pair
    window_spec = Window.partitionBy("route_pair").orderBy(col("origin"))
    df = df.withColumn("row_num", row_number().over(window_spec))
    df = df.filter(col("row_num") == 1).drop("row_num", "route_pair")
    
    # Add type column
    df = df.withColumn("type", lit(train_type))
    
    print(f"   Output records after cleaning: {df.count()}")
    
    return df


# FUNCTION: Validate data quality

def validate_data_quality(df, train_type):
    """
    Validate data quality and report issues
    """
    print(f"\n📊 Data Quality Report for {train_type} routes:")
    
    total = df.count()
    print(f"   Total records: {total}")
    
    critical_columns = ["origin", "destination", "route_name", "service_type"]
    
    for col_name in critical_columns:
        null_count = df.filter(col(col_name).isNull()).count()
        if null_count > 0:
            print(f"   ⚠ Warning: {null_count} null values in '{col_name}'")
    
    empty_origin = df.filter(trim(col("origin")) == "").count()
    empty_destination = df.filter(trim(col("destination")) == "").count()
    
    if empty_origin > 0:
        print(f"   ⚠ Warning: {empty_origin} empty origin values")
    if empty_destination > 0:
        print(f"   ⚠ Warning: {empty_destination} empty destination values")
    
    missing_origin_country = df.filter(col("origin_country").isNull()).count()
    missing_dest_country = df.filter(col("destination_country").isNull()).count()
    
    if missing_origin_country > 0:
        print(f"   ⚠ Warning: {missing_origin_country} routes missing origin_country")
    if missing_dest_country > 0:
        print(f"   ⚠ Warning: {missing_dest_country} routes missing destination_country")
    
    print(f"\n   Country distribution (origin):")
    df.groupBy("origin_country").count().orderBy(col("count").desc()).show()
    
    print(f"\n   Sample of cleaned data:")
    df.select("origin", "destination", "route_name_simple", "type", "origin_country", "destination_country") \
        .show(5, truncate=False)


# FUNCTION: Save cleaned data

def save_cleaned_data(df, output_path):
    """
    Save cleaned DataFrame to CSV
    """
    print(f"\n   Saving to: {output_path}")
    
    temp_path = output_path.replace('.csv', '_temp')
    
    df.coalesce(1).write.csv(
        temp_path,
        header=True,
        mode='overwrite'
    )
    
    import glob
    import shutil
    
    temp_files = glob.glob(temp_path + '/part-*.csv')
    if temp_files:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        shutil.move(temp_files[0], output_path)
        shutil.rmtree(temp_path)
        print(f"   ✓ Saved: {output_path}")
    else:
        print(f"   ❌ Error: No output files generated")


# MAIN TRANSFORMATION SCRIPT

def main():
    """Main execution function for transformation"""
    
    print("=" * 70)
    print("🔄 TRANSFORMATION PHASE: Cleaning and Standardizing Routes Data")
    print("=" * 70)
    
    spark = init_spark()
    
    if not os.path.exists(PROCESSED_FOLDER):
        os.makedirs(PROCESSED_FOLDER)
        print(f"✓ Created output directory: {PROCESSED_FOLDER}")
    
    # --- CLEAN NIGHT ROUTES ---
    print("\n" + "=" * 70)
    print("🌙 Processing NIGHT routes...")
    print("=" * 70)
    
    if os.path.exists(NIGHT_FILE):
        night_df = spark.read.csv(NIGHT_FILE, header=True, inferSchema=True)
        night_df_cleaned = clean_routes(spark, night_df, 'night')
        
        # --- EXCLUDE UNKNOWN countries ---
        night_df_cleaned = night_df_cleaned.filter(
            (col("origin_country").isNotNull()) &
            (col("destination_country").isNotNull()) &
            (col("origin_country") != "UNKNOWN") &
            (col("destination_country") != "UNKNOWN")
        )
        print(f"   Night records after excluding UNKNOWN countries: {night_df_cleaned.count()}")
        
        validate_data_quality(night_df_cleaned, 'night')
        
        night_cleaned_file = os.path.join(PROCESSED_FOLDER, 'night_routes_cleaned.csv')
        save_cleaned_data(night_df_cleaned, night_cleaned_file)
        
        print(f"\n✅ Night routes transformation complete!")
    else:
        print(f"❌ Night routes file not found: {NIGHT_FILE}")
    
    # --- CLEAN DAY ROUTES ---
    print("\n" + "=" * 70)
    print("☀️  Processing DAY routes...")
    print("=" * 70)
    
    if os.path.exists(DAY_FILE):
        day_df = spark.read.csv(DAY_FILE, header=True, inferSchema=True)
        day_df_cleaned = clean_routes(spark, day_df, 'day')
        
        validate_data_quality(day_df_cleaned, 'day')
        
        day_cleaned_file = os.path.join(PROCESSED_FOLDER, 'day_routes_cleaned.csv')
        save_cleaned_data(day_df_cleaned, day_cleaned_file)
        
        print(f"\n✅ Day routes transformation complete!")
    else:
        print(f"❌ Day routes file not found: {DAY_FILE}")
    
    # --- CREATE COMBINED DATASET ---
    print("\n" + "=" * 70)
    print("🔗 Creating COMBINED dataset...")
    print("=" * 70)
    
    if os.path.exists(NIGHT_FILE) and os.path.exists(DAY_FILE):
        night_clean = spark.read.csv(
            os.path.join(PROCESSED_FOLDER, 'night_routes_cleaned.csv'),
            header=True,
            inferSchema=True
        )
        day_clean = spark.read.csv(
            os.path.join(PROCESSED_FOLDER, 'day_routes_cleaned.csv'),
            header=True,
            inferSchema=True
        )
        
        combined_df = night_clean.union(day_clean)
        combined_df = combined_df.dropDuplicates(["origin", "destination", "route_name"])
        
        print(f"   Combined records: {combined_df.count()}")
        
        print(f"\n   Distribution by train type:")
        combined_df.groupBy("type").count().show()
        
        combined_file = os.path.join(PROCESSED_FOLDER, 'all_routes_cleaned.csv')
        save_cleaned_data(combined_df, combined_file)
        
        print(f"\n✅ Combined dataset created!")
        
        print("\n" + "=" * 70)
        print("📈 FINAL SUMMARY STATISTICS")
        print("=" * 70)
        print(f"   Total routes (combined): {combined_df.count()}")
        print(f"   Night routes: {night_clean.count()}")
        print(f"   Day routes: {day_clean.count()}")
        
        print(f"\n   Routes by country (origin):")
        combined_df.groupBy("origin_country", "type") \
            .count() \
            .orderBy(col("origin_country"), col("type")) \
            .show(truncate=False)
    
    spark.stop()
    print("\n" + "=" * 70)
    print("✅ Transformation phase complete - Spark session finished")
    print("=" * 70)

if __name__ == "__main__":
    main()
