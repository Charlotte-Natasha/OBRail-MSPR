from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, trim,  udf, lit, 
    concat,  when,  row_number
)
from pyspark.sql.types import StringType, DoubleType
from pyspark.sql.window import Window
from math import radians, cos, sin, asin, sqrt
import unicodedata
import re
import os
import glob
import shutil


# CONFIGURATION

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


# Initialize Spark Session

def init_spark():
    spark = SparkSession.builder \
        .appName("GTFS Night Routes Extraction") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


#  Normalize station names

def normalize_text(name):
    if not name or name.strip() == "":
        return ""
    name = name.lower().strip()
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = re.sub(r'[^a-z0-9 ]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

normalize_udf = udf(normalize_text, StringType())

# Simplify station names for dashboard

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

# Haversine distance calculation

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Handle None/null values
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    
    try:
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return round(c * r, 2)
    except (ValueError, TypeError):
        return None

# Register as UDF
haversine_udf = udf(haversine_distance, DoubleType())


# Resolve country with fallback

def resolve_country_from_station(station_normalized, folder_country):
    if folder_country is not None and folder_country != "":
        return folder_country
    
    if not station_normalized:
        return "UNKNOWN"
    
    station_norm = station_normalized.lower().strip()
    station_norm = unicodedata.normalize('NFKD', station_norm).encode('ascii', 'ignore').decode()
    station_norm = re.sub(r'[^a-z0-9 ]', '', station_norm)
    station_norm = re.sub(r'\s+', ' ', station_norm).strip()
    
    for key, code in STATION_COUNTRY_MAP.items():
        key_norm = key.lower().strip()
        if key_norm in station_norm or station_norm in key_norm:
            return code
    
    return "UNKNOWN"

resolve_country_udf = udf(resolve_country_from_station, StringType())

# FUNCTION: Extract routes from GTFS folder

def extract_routes_pyspark(spark, folder, folder_country):
    required_files = ["stops.txt", "trips.txt", "stop_times.txt", "routes.txt"]
    missing = [f for f in required_files if not os.path.exists(os.path.join(folder, f))]
    if missing:
        print(f"⚠ Skipping {folder}, missing files: {missing}")
        return None
    
    try:
        stops = spark.read.csv(os.path.join(folder, "stops.txt"), header=True, inferSchema=True)
        stop_times = spark.read.csv(os.path.join(folder, "stop_times.txt"), header=True, inferSchema=True)
        trips = spark.read.csv(os.path.join(folder, "trips.txt"), header=True, inferSchema=True)
        routes = spark.read.csv(os.path.join(folder, "routes.txt"), header=True, inferSchema=True)
        
        stop_times = stop_times.withColumn("stop_sequence", col("stop_sequence").cast("int"))
        
        window_spec = Window.partitionBy("trip_id").orderBy("stop_sequence")
        stop_times_with_rank = stop_times.withColumn("rank", row_number().over(window_spec))
        
        first_stops = stop_times_with_rank.filter(col("rank") == 1) \
            .select("trip_id", "stop_id") \
            .join(stops.select("stop_id", 
                            col("stop_name").alias("origin_name"),
                            col("stop_lat").alias("origin_lat"),
                            col("stop_lon").alias("origin_lon")), 
                on="stop_id", how="left")
        
        window_spec_desc = Window.partitionBy("trip_id").orderBy(col("stop_sequence").desc())
        stop_times_with_rank_desc = stop_times.withColumn("rank_desc", row_number().over(window_spec_desc))
        
        # Get last stops
        
        last_stops = stop_times_with_rank_desc.filter(col("rank_desc") == 1) \
            .select("trip_id", "stop_id") \
            .join(stops.select("stop_id", 
                            col("stop_name").alias("destination_name"),
                            col("stop_lat").alias("dest_lat"),
                            col("stop_lon").alias("dest_lon")), 
                on="stop_id", how="left")
            
        # Join trips with routes and stops to get origin/destination names    
        
        df = trips.join(routes.select("route_id", "route_short_name"), on="route_id", how="left")
        df = df.join(first_stops.select("trip_id", "origin_name", "origin_lat", "origin_lon"), 
                    on="trip_id", how="left")
        df = df.join(last_stops.select("trip_id", "destination_name", "dest_lat", "dest_lon"), 
                    on="trip_id", how="left")
        
        # Filter out null or empty stations
        
        df = df.filter(
            (col("origin_name").isNotNull()) & (col("destination_name").isNotNull()) &
            (trim(col("origin_name")) != "") & (trim(col("destination_name")) != "")
        )
        
        # Normalize station names
        df = df.withColumn("origin", normalize_udf(col("origin_name")))
        df = df.withColumn("destination", normalize_udf(col("destination_name")))
        df = df.withColumn("service_type", lit("night"))
        
        # create route_name based on route_short_name if available, otherwise use "origin → destination"
        
        df = df.withColumn(
            "route_name",
            when(
                (col("route_short_name").isNull()) |
                (trim(col("route_short_name")) == "") |
                (trim(col("route_short_name")) == trim(col("origin_name"))),
                concat(col("origin_name"), lit(" → "), col("destination_name"))
            ).otherwise(col("route_short_name"))
        )
        
        # Calculate distance using Haversine formula
        df = df.withColumn(
            "distance_km",
            haversine_udf(
                col("origin_lat"),
                col("origin_lon"),
                col("dest_lat"),
                col("dest_lon")
            )
        )
        
        # Remove routes with null distance
        df = df.filter(col("distance_km").isNotNull())
        
        # Create a sorted pair for deduplication of bidirectional routes
        df = df.withColumn(
            "station_pair",
            when(col("origin") < col("destination"),
                concat(col("origin"), lit("_"), col("destination")))
            .otherwise(concat(col("destination"), lit("_"), col("origin")))
        )
        
        df = df.dropDuplicates(["station_pair"])
        
        # Resolve country for origin and destination
        df = df.withColumn("origin_country", resolve_country_udf(col("origin"), lit(folder_country)))
        df = df.withColumn("destination_country", resolve_country_udf(col("destination"), lit(folder_country)))
        
        df = df.withColumn("origin_simple", simplify_station_udf(col("origin")))
        df = df.withColumn("destination_simple", simplify_station_udf(col("destination")))
        df = df.withColumn("route_name_simple", concat(col("origin_simple"), lit(" → "), col("destination_simple")))
        
        result = df.select(
            "route_name", "origin", "destination", "service_type",
            "route_name_simple", "origin_country", "destination_country", "distance_km"
        )
        return result
        
    except Exception as e:
        print(f"❌ Error processing {folder}: {str(e)}")
        return None


# MAIN SCRIPT

def main():
    print("🚀 Starting GTFS Night Routes Extraction with PySpark")
    spark = init_spark()
    
    all_routes = []
    for folder in GTFS_NIGHT_FOLDERS:
        print(f"\n➡ Processing folder: {folder}")
        folder_country = FOLDER_COUNTRY_MAP.get(folder)
        df_routes = extract_routes_pyspark(spark, folder, folder_country)
        if df_routes is not None and df_routes.count() > 0:
            print(f"   ✓ Extracted {df_routes.count()} routes")
            all_routes.append(df_routes)
        else:
            print("   No routes extracted")
    
    if all_routes:
        from functools import reduce
        master_night = reduce(lambda df1, df2: df1.union(df2), all_routes)
        master_night = master_night.dropDuplicates(["origin", "destination", "route_name"])
        
        output_dir = os.path.dirname(OUTPUT_FILE)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        temp_path = OUTPUT_FILE.replace('.csv', '_temp')
        master_night.coalesce(1).write.csv(temp_path, header=True, mode='overwrite')
        
        temp_files = glob.glob(temp_path + '/part-*.csv')
        if temp_files:
            shutil.move(temp_files[0], OUTPUT_FILE)
            shutil.rmtree(temp_path)
        
        print(f"\n✅ Master night routes CSV created: {OUTPUT_FILE}")
        master_night.groupBy("origin_country").count().orderBy(col("count").desc()).show()
        master_night.show(10, truncate=False)
    
    else:
        print("\n❌ No night routes were extracted from any folder")
    
    spark.stop()
    print("\n✅ Spark session finished")

if __name__ == "__main__":
    main()
