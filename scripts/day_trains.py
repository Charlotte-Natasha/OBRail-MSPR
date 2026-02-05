from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, trim, udf, lit, 
    concat,  when, row_number)
from pyspark.sql.types import StringType, DoubleType  
from pyspark.sql.window import Window
from math import radians, sin, cos, asin, sqrt
import unicodedata
import re
import os

# CONFIGURATION
GTFS_DAY_FOLDERS = [
    "data/raw/day/Denmark/",
    "data/raw/day/Eurostar_international/",
    "data/raw/day/France/",
    "data/raw/day/Germany/",
    "data/raw/day/Switzerland/"
]

OUTPUT_FILE = "data/extracted/day_routes.csv"

# Country code per folder
FOLDER_COUNTRY_MAP = {
    "data/raw/day/Denmark/": "DK",
    "data/raw/day/Eurostar_international/": None,
    "data/raw/day/France/": "FR",
    "data/raw/day/Germany/": "DE",
    "data/raw/day/Switzerland/": "CH"
}

# For cross-border folders, map origin stations to countries manually
STATION_COUNTRY_MAP = {
    "st pancras international": "GB",
    "london st pancras": "GB",
    "paris nord": "FR",
    "paris gare du nord": "FR",
    "bruxelles midi": "BE",
    "brussels midi": "BE",
    "amsterdam centraal": "NL",
    "rotterdam centraal": "NL",
    "lille europe": "FR",
    "calais ville": "FR",
    "dunkerque": "FR",
    "basel": "CH",
    "zurich": "CH",
    "koln": "DE",
    "cologne": "DE",
    "dortmund": "DE",
    "essen": "DE",
    "marne la vallee": "FR",
    "bourg st maurice": "FR",
}


# Initialize Spark Session

def init_spark():
    """Initialize and return a Spark session"""
    spark = SparkSession.builder \
        .appName("GTFS Day Routes Extraction") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark


# Normalize station names

def normalize_text(name):
    """Normalize station name by removing accents and special characters"""
    if not name or name.strip() == "":
        return ""
    name = name.lower().strip()
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = re.sub(r'[^a-z0-9 ]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

normalize_udf = udf(normalize_text, StringType())


# UDF: Simplify station for dashboard
def simplify_station_text(name):
    """Simplify station name for dashboard display"""
    if not name or name.strip() == "":
        return ""
    
    name = name.strip().lower()
    
    # Remove common terms
    remove_terms = ["bf", "hbf", "tief", "bad", "gare", "routiere"]
    pattern = r'\b(' + '|'.join(remove_terms) + r')\b'
    name = re.sub(pattern, '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Capitalize appropriately
    small_words = ["de", "du", "des", "la", "le", "les", "d'", "l'", "à"]
    words = []
    for w in name.split():
        if w in small_words:
            words.append(w)
        else:
            words.append(w.capitalize())
    
    return ' '.join(words)

simplify_station_udf = udf(simplify_station_text, StringType())

# UDF: Haversine distance calculation

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

# Resolve country from station name

def resolve_country_from_station(station_normalized, folder_country):
    """Resolve country code from station name for cross-border routes"""
    if folder_country is not None and folder_country != "":
        return folder_country
    
    for key, code in STATION_COUNTRY_MAP.items():
        if key in station_normalized.lower():
            return code
    
    return None

resolve_country_udf = udf(resolve_country_from_station, StringType())

# FUNCTION: Check if folder has required files

def check_required_files(folder):
    """Check which GTFS files are available in the folder"""
    files = os.listdir(folder) if os.path.exists(folder) else []
    
    return {
        'has_stops': 'stops.txt' in files,
        'has_trips': 'trips.txt' in files,
        'has_routes': 'routes.txt' in files,
        'has_stop_times': 'stop_times.txt' in files
    }


# FUNCTION: Extracts routes from a GTFS folder using PySpark

def extract_routes_pyspark(spark, folder, folder_country):
    """Extract routes from a GTFS folder using PySpark"""
    
    # Check required files
    file_status = check_required_files(folder)
    
    if not (file_status['has_stops'] and file_status['has_trips'] and file_status['has_routes']):
        print(f"⚠ Skipping {folder}, missing essential files")
        return None
    
    # If no stop_times.txt, check if trips.txt has start/end columns
    if not file_status['has_stop_times']:
        trips_check = spark.read.csv(
            os.path.join(folder, "trips.txt"),
            header=True,
            inferSchema=True
        )
        
        if 'start_stop_id' not in trips_check.columns or 'end_stop_id' not in trips_check.columns:
            print(f"⚠ Skipping {folder}, no stop_times.txt and no start/end stop columns in trips.txt")
            return None
    
    try:
        # Read GTFS files
        stops = spark.read.csv(
            os.path.join(folder, "stops.txt"),
            header=True,
            inferSchema=True
        )
        
        trips = spark.read.csv(
            os.path.join(folder, "trips.txt"),
            header=True,
            inferSchema=True
        )
        
        routes = spark.read.csv(
            os.path.join(folder, "routes.txt"),
            header=True,
            inferSchema=True
        )
        
        # Handle two cases: with stop_times.txt or without
        if file_status['has_stop_times']:
            # Case 1: Use stop_times.txt
            stop_times = spark.read.csv(
                os.path.join(folder, "stop_times.txt"),
                header=True,
                inferSchema=True
            )
            
            stop_times = stop_times.withColumn("stop_sequence", col("stop_sequence").cast("int"))
            
            # Get first stops
            window_spec_asc = Window.partitionBy("trip_id").orderBy("stop_sequence")
            stop_times_with_rank = stop_times.withColumn(
                "rank", row_number().over(window_spec_asc)
            )
            
            first_stops = stop_times_with_rank.filter(col("rank") == 1) \
            .select("trip_id", "stop_id") \
            .join(stops.select("stop_id", 
                            col("stop_name").alias("origin_name"),
                            col("stop_lat").alias("origin_lat"),
                            col("stop_lon").alias("origin_lon")), 
                on="stop_id", how="left")
            
            # Get last stops
            window_spec_desc = Window.partitionBy("trip_id").orderBy(col("stop_sequence").desc())
            stop_times_with_rank_desc = stop_times.withColumn(
                "rank_desc", row_number().over(window_spec_desc)
            )
            
            last_stops = stop_times_with_rank_desc.filter(col("rank_desc") == 1) \
            .select("trip_id", "stop_id") \
            .join(stops.select("stop_id", 
                            col("stop_name").alias("destination_name"),
                            col("stop_lat").alias("dest_lat"),
                            col("stop_lon").alias("dest_lon")), 
                on="stop_id", how="left")
        
        else:
            # Case 2: Use start_stop_id and end_stop_id from trips.txt
            first_stops = trips.select(
                col("trip_id"),
                col("start_stop_id").alias("stop_id")
            ).join(
                stops.select("stop_id", col("stop_name").alias("origin_name")),
                on="stop_id",
                how="left"
            )
            
            last_stops = trips.select(
                col("trip_id"),
                col("end_stop_id").alias("stop_id")
            ).join(
                stops.select("stop_id", col("stop_name").alias("destination_name")),
                on="stop_id",
                how="left"
            )
        
        # Join trips with routes and stops to get origin/destination names
        
        df = trips.join(
            routes.select("route_id", "route_short_name"), 
            on="route_id", 
            how="left"
        )
        
        df = df.join(first_stops.select("trip_id", "origin_name", "origin_lat", "origin_lon"), 
                    on="trip_id", how="left")
        df = df.join(last_stops.select("trip_id", "destination_name", "dest_lat", "dest_lon"), 
                    on="trip_id", how="left")
        
        # Filter out null or empty stations
        df = df.filter(
            (col("origin_name").isNotNull()) & 
            (col("destination_name").isNotNull()) &
            (trim(col("origin_name")) != "") &
            (trim(col("destination_name")) != "")
        )
        
        # Normalize station names
        df = df.withColumn("origin", normalize_udf(col("origin_name")))
        df = df.withColumn("destination", normalize_udf(col("destination_name")))
        
        # Set service type
        df = df.withColumn("service_type", lit("day"))
        
        # Create route_name - fix if empty or same as origin
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
        
        # Deduplicate bidirectional routes
        df = df.withColumn(
            "station_pair",
            when(col("origin") < col("destination"),
                concat(col("origin"), lit("_"), col("destination")))
            .otherwise(concat(col("destination"), lit("_"), col("origin")))
        )
        
        df = df.dropDuplicates(["station_pair"])
        
        # Resolve countries
        df = df.withColumn(
            "origin_country",
            resolve_country_udf(col("origin"), lit(folder_country))
        )
        
        df = df.withColumn(
            "destination_country",
            resolve_country_udf(col("destination"), lit(folder_country))
        )
        
        # Check for unresolved countries
        unresolved = df.filter(
            col("origin_country").isNull() | col("destination_country").isNull()
        )
        
        unresolved_count = unresolved.count()
        if unresolved_count > 0:
            print(f"   ⚠ {unresolved_count} routes with unresolved country:")
            unresolved.select("origin", "destination", "origin_country", "destination_country").show(truncate=False)
        
        # Create simplified names for dashboard
        df = df.withColumn("origin_simple", simplify_station_udf(col("origin")))
        df = df.withColumn("destination_simple", simplify_station_udf(col("destination")))
        df = df.withColumn(
            "route_name_simple",
            concat(col("origin_simple"), lit(" → "), col("destination_simple"))
        )
        
        # Select final columns
        result = df.select(
            "route_name",
            "origin",
            "destination",
            "service_type",
            "route_name_simple",
            "origin_country",
            "destination_country",
            "distance_km"
        )
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing {folder}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


# MAIN SCRIPT

def main():
    """Main execution function"""
    
    print("🚀 Starting GTFS Day Routes Extraction with PySpark")
    
    # Initialize Spark
    spark = init_spark()
    
    all_routes = []
    
    for folder in GTFS_DAY_FOLDERS:
        print(f"\n➡ Processing folder: {folder}")
        folder_country = FOLDER_COUNTRY_MAP.get(folder)
        
        df_routes = extract_routes_pyspark(spark, folder, folder_country)
        
        if df_routes is not None and df_routes.count() > 0:
            route_count = df_routes.count()
            print(f"   ✓ Extracted {route_count} routes")
            all_routes.append(df_routes)
        else:
            print("   No routes extracted")
    
    if all_routes:
        # Union all dataframes
        from functools import reduce
        master_day = reduce(lambda df1, df2: df1.union(df2), all_routes)
        
        # Remove duplicates across all sources
        master_day = master_day.dropDuplicates(["origin", "destination", "route_name"])
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(OUTPUT_FILE)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write to CSV (coalesce to single file)
        master_day.coalesce(1).write.csv(
            OUTPUT_FILE.replace('.csv', '_temp'),
            header=True,
            mode='overwrite'
        )
        
        # Rename the part file to the expected output name
        import glob
        temp_files = glob.glob(OUTPUT_FILE.replace('.csv', '_temp') + '/part-*.csv')
        if temp_files:
            import shutil
            shutil.move(temp_files[0], OUTPUT_FILE)
            shutil.rmtree(OUTPUT_FILE.replace('.csv', '_temp'))
        
        total_routes = master_day.count()
        print(f"\n✅ Master day routes CSV created: {OUTPUT_FILE}")
        print(f"Total routes: {total_routes}")
        
        print(f"\nCountry breakdown (origin):")
        master_day.groupBy("origin_country").count().orderBy(col("count").desc()).show()
        
        print(f"\nSample routes:")
        master_day.show(10, truncate=False)
        
    else:
        print("\n❌ No day routes were extracted from any folder")
    
    # Stop Spark session
    spark.stop()
    print("\n✅ Spark session finished")

if __name__ == "__main__":
    main()