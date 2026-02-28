from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, trim, udf, lit,
    concat, when, row_number
)
from pyspark.sql.functions import round as spark_round
from pyspark.sql.types import StringType, DoubleType
from pyspark.sql.window import Window
from math import radians, cos, sin, asin, sqrt
from functools import reduce
import unicodedata
import re
import os
import glob
import shutil
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
        logging.FileHandler("logs/night_trains.log")
    ]
)
logger = logging.getLogger("night_trains")

# ============================================
# CONFIGURATION
# ============================================

GTFS_NIGHT_FOLDERS = [
    "data/raw/night/Switzerland/",
    "data/raw/night/long_distance/",
    "data/raw/night/sncf-data/",
    "data/raw/night/open_data/",
    "data/raw/night/long_distance_rail/"
]

OUTPUT_FILE = "data/extracted/night_routes.csv"

FOLDER_COUNTRY_MAP = {
    "data/raw/night/Switzerland/": "CH",
    "data/raw/night/long_distance/": None,
    "data/raw/night/sncf-data/": "FR",
    "data/raw/night/open_data/": None,
    "data/raw/night/long_distance_rail/": None
}

STATION_COUNTRY_MAP = {
    "basel": "CH", "zurich": "CH", "brig": "CH", "lausanne": "CH",
    "geneve": "CH", "geneva": "CH", "montreux": "CH", "olten": "CH",
    "liestal": "CH", "como": "IT", "chiasso": "IT", "lugano": "IT",
    "bellinzona": "IT", "domodossola": "IT", "simplontunnel": "IT",
    "paris nord": "FR", "paris gare du nord": "FR", "lyon": "FR",
    "marseille": "FR", "nice": "FR", "bruxelles midi": "BE",
    "brussels midi": "BE", "amsterdam centraal": "NL", "rotterdam centraal": "NL",
    "wien": "AT", "vienna": "AT", "munchen": "DE", "munich": "DE",
    "berlin": "DE", "hamburg": "DE", "koln": "DE", "cologne": "DE",
    "frankfurt": "DE", "salzburg": "AT", "innsbruck": "AT", "graz": "AT",
    "prague": "CZ", "budapest": "HU",
}


# ============================================
# SPARK INIT
# ============================================

def init_spark():
    spark = SparkSession.builder \
        .appName("GTFS Night Routes Extraction") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


# ============================================
# UDFs
# ============================================

def normalize_text(name):
    if not name or name.strip() == "":
        return ""
    name = name.lower().strip()
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = re.sub(r'[^a-z0-9 ]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

normalize_udf = udf(normalize_text, StringType())


def simplify_station_text(name):
    if not name or name.strip() == "":
        return ""
    name = name.strip().lower()
    remove_terms = ["bf", "hbf", "tief", "bad", "gare", "routiere"]
    pattern = r'\b(' + '|'.join(remove_terms) + r')\b'
    name = re.sub(pattern, '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    small_words = ["de", "du", "des", "la", "le", "les", "d'", "l'", "à"]
    words = []
    for w in name.split():
        words.append(w if w in small_words else w.capitalize())
    return ' '.join(words)

simplify_station_udf = udf(simplify_station_text, StringType())


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate great circle distance in km using Haversine formula"""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return round(c * 6371, 2)
    except (ValueError, TypeError):
        return None

haversine_udf = udf(haversine_distance, DoubleType())


def resolve_country_from_station(station_normalized, folder_country):
    if folder_country is not None and folder_country != "":
        return folder_country
    if not station_normalized:
        return None
    station_norm = station_normalized.lower().strip()
    station_norm = unicodedata.normalize('NFKD', station_norm).encode('ascii', 'ignore').decode()
    station_norm = re.sub(r'[^a-z0-9 ]', '', station_norm)
    station_norm = re.sub(r'\s+', ' ', station_norm).strip()
    for key, code in STATION_COUNTRY_MAP.items():
        key_norm = key.lower().strip()
        if key_norm in station_norm or station_norm in key_norm:
            return code
    return None

resolve_country_udf = udf(resolve_country_from_station, StringType())


# ============================================
# EXTRACTION
# ============================================

def extract_routes_pyspark(spark, folder, folder_country):
    required_files = ["stops.txt", "trips.txt", "stop_times.txt", "routes.txt"]
    missing = [f for f in required_files if not os.path.exists(os.path.join(folder, f))]
    if missing:
        logger.warning(f"Skipping {folder} — missing files: {missing}")
        return None

    try:
        stops = spark.read.csv(os.path.join(folder, "stops.txt"), header=True, inferSchema=True)
        stop_times = spark.read.csv(os.path.join(folder, "stop_times.txt"), header=True, inferSchema=True)
        trips = spark.read.csv(os.path.join(folder, "trips.txt"), header=True, inferSchema=True)
        routes = spark.read.csv(os.path.join(folder, "routes.txt"), header=True, inferSchema=True)

        stop_times = stop_times.withColumn("stop_sequence", col("stop_sequence").cast("int"))

        window_asc = Window.partitionBy("trip_id").orderBy("stop_sequence")
        first_stops = stop_times.withColumn("rank", row_number().over(window_asc)) \
            .filter(col("rank") == 1).select("trip_id", "stop_id") \
            .join(stops.select("stop_id",
                               col("stop_name").alias("origin_name"),
                               col("stop_lat").alias("origin_lat"),
                               col("stop_lon").alias("origin_lon")),
                  on="stop_id", how="left")

        window_desc = Window.partitionBy("trip_id").orderBy(col("stop_sequence").desc())
        last_stops = stop_times.withColumn("rank_desc", row_number().over(window_desc)) \
            .filter(col("rank_desc") == 1).select("trip_id", "stop_id") \
            .join(stops.select("stop_id",
                               col("stop_name").alias("destination_name"),
                               col("stop_lat").alias("dest_lat"),
                               col("stop_lon").alias("dest_lon")),
                  on="stop_id", how="left")

        df = trips.join(routes.select("route_id", "route_short_name"), on="route_id", how="left")
        df = df.join(first_stops.select("trip_id", "origin_name", "origin_lat", "origin_lon"), on="trip_id", how="left")
        df = df.join(last_stops.select("trip_id", "destination_name", "dest_lat", "dest_lon"), on="trip_id", how="left")

        df = df.filter(
            (col("origin_name").isNotNull()) & (col("destination_name").isNotNull()) &
            (trim(col("origin_name")) != "") & (trim(col("destination_name")) != "")
        )

        df = df.withColumn("origin", normalize_udf(col("origin_name")))
        df = df.withColumn("destination", normalize_udf(col("destination_name")))
        df = df.withColumn("service_type", lit("night"))
        df = df.withColumn(
            "route_name",
            when(
                (col("route_short_name").isNull()) |
                (trim(col("route_short_name")) == "") |
                (trim(col("route_short_name")) == trim(col("origin_name"))),
                concat(col("origin_name"), lit(" → "), col("destination_name"))
            ).otherwise(col("route_short_name"))
        )
        df = df.withColumn("distance_km", haversine_udf(col("origin_lat"), col("origin_lon"), col("dest_lat"), col("dest_lon")))
        df = df.filter(col("distance_km").isNotNull())
        df = df.withColumn(
            "station_pair",
            when(col("origin") < col("destination"),
                 concat(col("origin"), lit("_"), col("destination")))
            .otherwise(concat(col("destination"), lit("_"), col("origin")))
        )
        df = df.withColumn("origin_country", resolve_country_udf(col("origin"), lit(folder_country)))
        df = df.withColumn("destination_country", resolve_country_udf(col("destination"), lit(folder_country)))

        unresolved_count = df.filter(col("origin_country").isNull() | col("destination_country").isNull()).count()
        if unresolved_count > 0:
            logger.warning(f"{unresolved_count} routes with unresolved country in {folder}")

        df = df.withColumn("origin_simple", simplify_station_udf(col("origin")))
        df = df.withColumn("destination_simple", simplify_station_udf(col("destination")))
        df = df.withColumn("route_name_simple", concat(col("origin_simple"), lit(" → "), col("destination_simple")))

        return df.select(
            "route_name", "origin", "destination", "service_type",
            "route_name_simple", "origin_country", "destination_country", "distance_km"
        )

    except Exception as e:
        logger.error(f"Error processing {folder}: {str(e)}")
        return None


# ============================================
# MAIN
# ============================================

def main():
    logger.info("Starting GTFS Night Routes Extraction with PySpark")
    spark = init_spark()
    all_routes = []

    for folder in GTFS_NIGHT_FOLDERS:
        logger.info(f"Processing folder: {folder}")
        folder_country = FOLDER_COUNTRY_MAP.get(folder)
        df_routes = extract_routes_pyspark(spark, folder, folder_country)
        if df_routes is not None and df_routes.count() > 0:
            logger.info(f"Extracted {df_routes.count()} routes from {folder}")
            all_routes.append(df_routes)
        else:
            logger.warning(f"No routes extracted from {folder}")

    if all_routes:
        master_night = reduce(lambda df1, df2: df1.union(df2), all_routes)
        logger.info(f"Combined routes before deduplication: {master_night.count()}")

        master_night = master_night.withColumn(
            "station_pair",
            when(col("origin") < col("destination"),
                 concat(col("origin"), lit("_"), col("destination")))
            .otherwise(concat(col("destination"), lit("_"), col("origin")))
        )
        master_night = master_night.withColumn("distance_norm", spark_round(col("distance_km"), 0))

        w = Window.partitionBy("station_pair", "distance_norm").orderBy("route_name")
        master_night = (master_night
                        .withColumn("rn", row_number().over(w))
                        .filter(col("rn") == 1)
                        .drop("rn", "station_pair", "distance_norm"))

        final_count = master_night.count()
        logger.info(f"Final routes after deduplication: {final_count}")

        try:
            output_dir = os.path.dirname(OUTPUT_FILE)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            temp_path = OUTPUT_FILE.replace('.csv', '_temp')
            master_night.coalesce(1).write.csv(temp_path, header=True, mode='overwrite')

            temp_files = glob.glob(temp_path + '/part-*.csv')
            if temp_files:
                shutil.move(temp_files[0], OUTPUT_FILE)
                shutil.rmtree(temp_path)
                logger.info(f"Night routes CSV saved: {OUTPUT_FILE} ({final_count} routes)")
            else:
                logger.error("No output file found after Spark write")

        except Exception as e:
            logger.error(f"Failed to write output file: {str(e)}")

        master_night.groupBy("origin_country").count().orderBy(col("count").desc()).show()
        master_night.select(
            "route_name", "origin", "destination",
            "origin_country", "destination_country", "distance_km"
        ).show(10, truncate=False)

    else:
        logger.error("No night routes were extracted from any folder")

    spark.stop()
    logger.info("Spark session finished")


if __name__ == "__main__":
    main()