from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, trim, when, concat, lit, udf, row_number
)
from pyspark.sql.functions import round as spark_round
from pyspark.sql.types import StringType
from pyspark.sql.window import Window
import os
import glob
import shutil
import unicodedata
import re
import logging

# ============================================
# LOGGING SETUP
# ============================================

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/clean_routes.log")
    ]
)
logger = logging.getLogger("clean_routes")

# ============================================
# CONFIGURATION
# ============================================

NIGHT_FILE = "data/extracted/night_routes.csv"
DAY_FILE = "data/extracted/day_routes.csv"
PROCESSED_FOLDER = "data/transformed/"
DISTANCE_TOLERANCE = 5.0  # km


# ============================================
# SPARK INIT
# ============================================

def init_spark():
    spark = SparkSession.builder \
        .appName("GTFS Routes Transformation") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


# ============================================
# UDFs
# ============================================

def normalize_station_name(name):
    """
    Normalize station names to catch duplicates:
    - 'Brest F' -> 'brest' (remove single trailing letters)
    - Accents: 'Köln' -> 'koln'
    - Remove operator suffixes (sncf, db, etc)
    """
    if not name or name.strip() == "":
        return ""

    name = name.lower().strip()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')

    # Remove single trailing letters (Brest F -> Brest)
    name = re.sub(r'\s+[a-z]$', '', name)

    # Remove station type words — keep direction words (nord, midi, est, sud)
    remove_patterns = [
        r'\bgare\b', r'\bbahnhof\b', r'\bhbf\b', r'\bbf\b',
        r'\bhauptbahnhof\b', r'\bstation\b', r'\bst\.?\b',
        r'\bsaint\b', r'\bsan\b',
        r'\b(sncf|db|oebb|trenitalia|renfe|ns|sj)\b',
    ]
    for pattern in remove_patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    return name

normalize_station_udf = udf(normalize_station_name, StringType())
title_case_udf = udf(lambda x: x.strip().title() if x else "", StringType())


# ============================================
# HELPERS
# ============================================

def clean_routes(df, train_type):
    """Standardize basic columns and add type"""
    df = df.withColumn("origin", title_case_udf(col("origin"))) \
           .withColumn("destination", title_case_udf(col("destination"))) \
           .withColumn("type", lit(train_type))
    return df


def save_cleaned_data(df, output_path):
    """Write Spark DataFrame to a single CSV file"""
    try:
        temp_path = output_path.replace('.csv', '_temp')
        df.coalesce(1).write.csv(temp_path, header=True, mode='overwrite')

        temp_files = glob.glob(temp_path + '/part-*.csv')
        if temp_files:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            shutil.move(temp_files[0], output_path)
            shutil.rmtree(temp_path)
            logger.info(f"Saved: {output_path}")
        else:
            logger.error(f"No output file found after Spark write for {output_path}")
    except Exception as e:
        logger.error(f"Failed to save {output_path}: {str(e)}")


# ============================================
# MAIN
# ============================================

def main():
    logger.info("Starting transformation phase — cleaning and standardizing routes")
    spark = init_spark()

    if not os.path.exists(PROCESSED_FOLDER):
        os.makedirs(PROCESSED_FOLDER)

    # 1. Load, clean and save individual files
    night_df = None
    day_df = None

    if os.path.exists(NIGHT_FILE):
        logger.info("Processing night routes")
        night_raw = spark.read.csv(NIGHT_FILE, header=True, inferSchema=True)
        night_df = clean_routes(night_raw, 'night').filter(
            col("origin_country").isNotNull() & col("destination_country").isNotNull()
        )
        night_count = night_df.count()
        logger.info(f"Night routes after filtering nulls: {night_count}")
        night_clean_file = os.path.join(PROCESSED_FOLDER, 'night_routes_cleaned.csv')
        save_cleaned_data(night_df, night_clean_file)
    else:
        logger.warning(f"Night routes file not found: {NIGHT_FILE}")

    if os.path.exists(DAY_FILE):
        logger.info("Processing day routes")
        day_raw = spark.read.csv(DAY_FILE, header=True, inferSchema=True)
        day_df = clean_routes(day_raw, 'day').filter(
            col("origin_country").isNotNull() & col("destination_country").isNotNull()
        )
        day_count = day_df.count()
        logger.info(f"Day routes after filtering nulls: {day_count}")
        day_clean_file = os.path.join(PROCESSED_FOLDER, 'day_routes_cleaned.csv')
        save_cleaned_data(day_df, day_clean_file)
    else:
        logger.warning(f"Day routes file not found: {DAY_FILE}")

    # 2. Combine datasets
    if night_df is None or day_df is None:
        logger.error("Could not load both night and day files — aborting")
        spark.stop()
        return

    logger.info("Creating combined dataset")
    combined_df = night_df.union(day_df)
    before_dedup = combined_df.count()
    logger.info(f"Combined routes before deduplication: {before_dedup}")

    # 3. Robust deduplication
    combined_df = combined_df \
        .withColumn("o_norm", normalize_station_udf(col("origin"))) \
        .withColumn("d_norm", normalize_station_udf(col("destination")))

    # Canonical key: sort normalized names so A->B == B->A
    combined_df = combined_df.withColumn(
        "route_key",
        when(col("o_norm") < col("d_norm"),
             concat(col("o_norm"), lit("_"), col("d_norm")))
        .otherwise(concat(col("d_norm"), lit("_"), col("o_norm")))
    )

    # Distance bucketing: routes within 5km tolerance are treated as the same
    combined_df = combined_df.withColumn(
        "dist_key", spark_round(col("distance_km") / DISTANCE_TOLERANCE)
    )

    # Prefer night over day, then alphabetical as tie-breaker
    w = Window.partitionBy("route_key", "dist_key").orderBy(
        col("type").desc(),   # night > day
        col("origin").asc()   # alphabetical tie-break
    )

    final_df = combined_df \
        .withColumn("rn", row_number().over(w)) \
        .filter(col("rn") == 1) \
        .drop("rn", "o_norm", "d_norm", "route_key", "dist_key")

    after_dedup = final_df.count()
    duplicates_removed = before_dedup - after_dedup
    logger.info(f"After deduplication: {after_dedup} routes ({duplicates_removed} duplicates removed)")

    # 4. Save combined file
    combined_file = os.path.join(PROCESSED_FOLDER, 'all_routes_cleaned.csv')
    save_cleaned_data(final_df, combined_file)

    # 5. Summary
    logger.info("Route type breakdown:")
    final_df.groupBy("type").count().show()
    final_df.select(
        "origin", "destination", "origin_country",
        "destination_country", "distance_km", "type"
    ).show(10, truncate=False)

    spark.stop()
    logger.info("Transformation phase complete")


if __name__ == "__main__":
    main()