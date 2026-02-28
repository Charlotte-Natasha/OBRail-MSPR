from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, trim, when, concat, lit, udf, row_number
)
from pyspark.sql.functions import round as spark_round
from pyspark.sql.types import StringType
from pyspark.sql.window import Window
import os
import unicodedata
import re

# CONFIGURATION
NIGHT_FILE = 'data/extracted/night_routes.csv'
DAY_FILE = 'data/extracted/day_routes.csv'
PROCESSED_FOLDER = 'data/transformed/'
DISTANCE_TOLERANCE = 5.0  # km

def init_spark():
    spark = SparkSession.builder \
        .appName("GTFS Routes Transformation") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark

def normalize_station_name(name):
    """
    Normalize station names to catch duplicates like:
    - 'Brest F' -> 'brest' (remove single trailing letters)
    - 'Paris Gare du Nord' -> 'paris gare du nord' (keep but lowercase)
    - Accents: 'Köln' -> 'koln'
    """
    if not name or name.strip() == "":
        return ""
    
    # Lowercase and remove accents
    name = name.lower().strip()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    
    # Remove single trailing letters (Brest F -> Brest)
    name = re.sub(r'\s+[a-z]$', '', name)
    
    # Remove station type words (gare, bahnhof, etc) but KEEP direction (nord, midi, est, sud)
    remove_patterns = [
        r'\bgare\b', r'\bbahnhof\b', r'\bhbf\b', r'\bbf\b',
        r'\bhauptbahnhof\b', r'\bstation\b', r'\bst\.?\b',
        r'\bsaint\b', r'\bsan\b',
        r'\b(sncf|db|oebb|trenitalia|renfe|ns|sj)\b',
    ]
    
    for pattern in remove_patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # Cleanup: keep alphanumeric + spaces
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

normalize_station_udf = udf(normalize_station_name, StringType())
title_case_udf = udf(lambda x: x.strip().title() if x else "", StringType())

def clean_routes(df, train_type):
    """Standardize basic columns and add type"""
    df = df.withColumn("origin", title_case_udf(col("origin"))) \
        .withColumn("destination", title_case_udf(col("destination"))) \
        .withColumn("type", lit(train_type))
    return df

def save_cleaned_data(df, output_path):
    temp_path = output_path.replace('.csv', '_temp')
    df.coalesce(1).write.csv(temp_path, header=True, mode='overwrite')
    
    import glob
    import shutil
    temp_files = glob.glob(temp_path + '/part-*.csv')
    if temp_files:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir): os.makedirs(output_dir)
        shutil.move(temp_files[0], output_path)
        shutil.rmtree(temp_path)

def main():
    spark = init_spark()
    if not os.path.exists(PROCESSED_FOLDER): os.makedirs(PROCESSED_FOLDER)

    print("=" * 70)
    print("🔄 TRANSFORMATION PHASE: Cleaning and Standardizing Routes Data")
    print("=" * 70)

    # 1. Load, Clean, and Save Individual Files
    night_df = None
    day_df = None
    
    if os.path.exists(NIGHT_FILE):
        print("\n🌙 Processing NIGHT routes...")
        night_raw = spark.read.csv(NIGHT_FILE, header=True, inferSchema=True)
        night_df = clean_routes(night_raw, 'night').filter(
            (col("origin_country") != "UNKNOWN") & (col("destination_country") != "UNKNOWN")
        )
        print(f"   Night routes loaded: {night_df.count()}")
        night_clean_file = os.path.join(PROCESSED_FOLDER, 'night_routes_cleaned.csv')
        save_cleaned_data(night_df, night_clean_file)
        print(f"   ✓ Saved: {night_clean_file}")

    if os.path.exists(DAY_FILE):
        print("\n☀️  Processing DAY routes...")
        day_raw = spark.read.csv(DAY_FILE, header=True, inferSchema=True)
        day_df = clean_routes(day_raw, 'day').filter(
            (col("origin_country") != "UNKNOWN") & (col("destination_country") != "UNKNOWN")
        )
        print(f"   Day routes loaded: {day_df.count()}")
        day_clean_file = os.path.join(PROCESSED_FOLDER, 'day_routes_cleaned.csv')
        save_cleaned_data(day_df, day_clean_file)
        print(f"   ✓ Saved: {day_clean_file}")

    # 2. Combine Datasets
    print("\n🔗 Creating COMBINED dataset...")
    if night_df is None or day_df is None:
        print("❌ Could not load both night and day files")
        spark.stop()
        return

    combined_df = night_df.union(day_df)
    night_count = night_df.count()
    day_count = day_df.count()
    before_dedup = combined_df.count()
    
    print(f"   Night routes: {night_count}")
    print(f"   Day routes: {day_count}")
    print(f"   Combined (before dedup): {before_dedup}")

    # 3. Robust Deduplication Strategy
    # Normalize names, create canonical route key, bucket distances, deduplicate
    
    combined_df = combined_df.withColumn("o_norm", normalize_station_udf(col("origin"))) \
                            .withColumn("d_norm", normalize_station_udf(col("destination")))

    # Canonical key: sort normalized names so A->B == B->A
    combined_df = combined_df.withColumn("route_key", 
        when(col("o_norm") < col("d_norm"), concat(col("o_norm"), lit("_"), col("d_norm")))
        .otherwise(concat(col("d_norm"), lit("_"), col("o_norm")))
    )

    # Distance bucketing: routes within 5km match (918.28 and 918.33 both -> bucket 919)
    combined_df = combined_df.withColumn("dist_key", spark_round(col("distance_km") / DISTANCE_TOLERANCE))

    # Deduplicate: prefer night, then alphabetical origin for tie-breaking
    w = Window.partitionBy("route_key", "dist_key").orderBy(
        col("type").desc(),      # night > day
        col("origin").asc()      # alphabetical tie-break
    )

    final_df = combined_df.withColumn("rn", row_number().over(w)) \
                        .filter(col("rn") == 1) \
                        .drop("rn", "o_norm", "d_norm", "route_key", "dist_key")

    after_dedup = final_df.count()
    duplicates_removed = before_dedup - after_dedup

    # 4. Save and Report
    print("\n   📊 DEDUPLICATION STATISTICS:")
    print(f"      Combined (before dedup): {before_dedup}")
    print(f"      Combined (after dedup): {after_dedup}")
    print(f"      Duplicates removed: {duplicates_removed}")

    print("\n" + "=" * 70)
    print("📈 FINAL SUMMARY")
    print("=" * 70)
    final_df.groupBy("type").count().show()
    
    combined_file = os.path.join(PROCESSED_FOLDER, 'all_routes_cleaned.csv')
    save_cleaned_data(final_df, combined_file)
    print(f"\n✅ Final output saved: {combined_file}")
    
    print("\n   Sample of final data:")
    final_df.select("origin", "destination", "origin_country", "destination_country", "distance_km", "type").show(10, truncate=False)
    
    spark.stop()
    print("\n✅ Transformation phase complete")

if __name__ == "__main__":
    main()