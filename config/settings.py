"""
ETL Configuration File
======================

Central configuration for all ETL scripts.
Modify paths here to match your folder structure.
"""

import os

# ----------------------------
# PROJECT STRUCTURE CONFIGURATION
# ----------------------------

# Determine if scripts are in 'scripts/' folder or project root
# Set this to True if you put scripts in scripts/ folder
SCRIPTS_IN_SUBFOLDER = False

# Base path adjustment
if SCRIPTS_IN_SUBFOLDER:
    BASE_PATH = "../"  # Go up one level from scripts/
else:
    BASE_PATH = ""     # Scripts are in project root

# ----------------------------
# DIRECTORY PATHS
# ----------------------------

# Raw data directories
RAW_DATA_DIR = os.path.join(BASE_PATH, "data/raw/")
RAW_NIGHT_DIR = os.path.join(RAW_DATA_DIR, "night/")
RAW_DAY_DIR = os.path.join(RAW_DATA_DIR, "day/")

# Processed data directories
EXTRACTED_DIR = os.path.join(BASE_PATH, "data/extracted/")
TRANSFORMED_DIR = os.path.join(BASE_PATH, "data/transformed/")

# Logs directory
LOGS_DIR = os.path.join(BASE_PATH, "logs/")

# ----------------------------
# GTFS SOURCE FOLDERS
# ----------------------------

# Night train GTFS folders
# Modify these based on what you actually downloaded
GTFS_NIGHT_FOLDERS = [
    os.path.join(RAW_NIGHT_DIR, "Switzerland/"),
    os.path.join(RAW_NIGHT_DIR, "long_distance/"),
    os.path.join(RAW_NIGHT_DIR, "sncf-data/"),
    os.path.join(RAW_NIGHT_DIR, "open_data/"),
    os.path.join(RAW_NIGHT_DIR, "long_distance_rail/"),
]

# Day train GTFS folders
# Modify these based on what you actually downloaded
GTFS_DAY_FOLDERS = [
    os.path.join(RAW_DAY_DIR, "Denmark/"),
    os.path.join(RAW_DAY_DIR, "Eurostar_international/"),
    os.path.join(RAW_DAY_DIR, "France/"),
    os.path.join(RAW_DAY_DIR, "Germany/"),
    os.path.join(RAW_DAY_DIR, "Switzerland/"),
]

# ----------------------------
# OUTPUT FILE PATHS
# ----------------------------

# Extracted data files
NIGHT_ROUTES_EXTRACTED = os.path.join(EXTRACTED_DIR, "night_routes.csv")
DAY_ROUTES_EXTRACTED = os.path.join(EXTRACTED_DIR, "day_routes.csv")

# Transformed data files
NIGHT_ROUTES_CLEANED = os.path.join(TRANSFORMED_DIR, "night_routes_cleaned.csv")
DAY_ROUTES_CLEANED = os.path.join(TRANSFORMED_DIR, "day_routes_cleaned.csv")
ALL_ROUTES_CLEANED = os.path.join(TRANSFORMED_DIR, "all_routes_cleaned.csv")

# ----------------------------
# COUNTRY MAPPING CONFIGURATION
# ----------------------------

# Country code per folder for night trains
# None = cross-border, will be resolved per station
NIGHT_FOLDER_COUNTRY_MAP = {
    os.path.join(RAW_NIGHT_DIR, "Switzerland/"): "CH",
    os.path.join(RAW_NIGHT_DIR, "long_distance/"): None,
    os.path.join(RAW_NIGHT_DIR, "sncf-data/"): "FR",
    os.path.join(RAW_NIGHT_DIR, "open_data/"): None,
    os.path.join(RAW_NIGHT_DIR, "long_distance_rail/"): None,
}

# Country code per folder for day trains
DAY_FOLDER_COUNTRY_MAP = {
    os.path.join(RAW_DAY_DIR, "Denmark/"): "DK",
    os.path.join(RAW_DAY_DIR, "Eurostar_international/"): None,
    os.path.join(RAW_DAY_DIR, "France/"): "FR",
    os.path.join(RAW_DAY_DIR, "Germany/"): "DE",
    os.path.join(RAW_DAY_DIR, "Switzerland/"): "CH",
}

# Station to country mapping (for cross-border routes)
# Add more stations as needed
STATION_COUNTRY_MAP = {
    # Switzerland
    "basel": "CH",
    "zurich": "CH",
    "brig": "CH",
    "lausanne": "CH",
    "geneve": "CH",
    "geneva": "CH",
    "montreux": "CH",
    "olten": "CH",
    "liestal": "CH",
    
    # Italy
    "como": "IT",
    "chiasso": "IT",
    "lugano": "IT",
    "bellinzona": "IT",
    "domodossola": "IT",
    "simplontunnel": "IT",
    "milano": "IT",
    "milan": "IT",
    "roma": "IT",
    "rome": "IT",
    
    # France
    "paris nord": "FR",
    "paris gare du nord": "FR",
    "lyon": "FR",
    "marseille": "FR",
    "nice": "FR",
    "lille europe": "FR",
    "calais ville": "FR",
    "dunkerque": "FR",
    "marne la vallee": "FR",
    "bourg st maurice": "FR",
    
    # Belgium
    "bruxelles midi": "BE",
    "brussels midi": "BE",
    
    # Netherlands
    "amsterdam centraal": "NL",
    "rotterdam centraal": "NL",
    
    # Austria
    "wien": "AT",
    "vienna": "AT",
    "salzburg": "AT",
    "innsbruck": "AT",
    "graz": "AT",
    
    # Germany
    "munchen": "DE",
    "munich": "DE",
    "berlin": "DE",
    "hamburg": "DE",
    "koln": "DE",
    "cologne": "DE",
    "frankfurt": "DE",
    "dortmund": "DE",
    "essen": "DE",
    
    # United Kingdom
    "st pancras international": "GB",
    "london st pancras": "GB",
    
    # Czech Republic
    "prague": "CZ",
    "praha": "CZ",
    
    # Hungary
    "budapest": "HU",
}

# ----------------------------
# PYSPARK CONFIGURATION
# ----------------------------

SPARK_APP_NAME = "ObRail_ETL_Pipeline"
SPARK_DRIVER_MEMORY = "4g"
SPARK_SHUFFLE_PARTITIONS = "10"

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def create_directories():
    """Create all necessary directories if they don't exist"""
    directories = [
        EXTRACTED_DIR,
        TRANSFORMED_DIR,
        LOGS_DIR,
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")

def validate_gtfs_folders():
    """Check which GTFS folders actually exist"""
    print("\n📂 Validating GTFS folder structure...")
    
    all_folders = GTFS_NIGHT_FOLDERS + GTFS_DAY_FOLDERS
    existing = []
    missing = []
    
    for folder in all_folders:
        if os.path.exists(folder):
            # Check if it has GTFS files
            files = os.listdir(folder) if os.path.isdir(folder) else []
            gtfs_files = [f for f in files if f.endswith('.txt')]
            
            if gtfs_files:
                existing.append(folder)
                print(f"   ✓ Found: {folder} ({len(gtfs_files)} .txt files)")
            else:
                missing.append(folder)
                print(f"   ⚠ Empty: {folder} (no .txt files)")
        else:
            missing.append(folder)
            print(f"   ✗ Missing: {folder}")
    
    print(f"\n   Summary: {len(existing)} valid, {len(missing)} missing/empty")
    
    return existing, missing

def get_actual_gtfs_folders(folder_type="both"):
    """
    Get only the GTFS folders that actually exist
    
    Args:
        folder_type: "night", "day", or "both"
    
    Returns:
        List of existing folder paths
    """
    if folder_type == "night":
        folders = GTFS_NIGHT_FOLDERS
    elif folder_type == "day":
        folders = GTFS_DAY_FOLDERS
    else:
        folders = GTFS_NIGHT_FOLDERS + GTFS_DAY_FOLDERS
    
    return [f for f in folders if os.path.exists(f)]

# ----------------------------
# CONFIGURATION SUMMARY
# ----------------------------

def print_configuration():
    """Print current configuration"""
    print("=" * 70)
    print("ETL PIPELINE CONFIGURATION")
    print("=" * 70)
    print(f"\n📁 Project Structure:")
    print(f"   Scripts location: {'scripts/' if SCRIPTS_IN_SUBFOLDER else 'project root'}")
    print(f"   Base path: {os.path.abspath(BASE_PATH)}")
    
    print(f"\n📂 Data Directories:")
    print(f"   Raw data: {os.path.abspath(RAW_DATA_DIR)}")
    print(f"   Extracted: {os.path.abspath(EXTRACTED_DIR)}")
    print(f"   Transformed: {os.path.abspath(TRANSFORMED_DIR)}")
    print(f"   Logs: {os.path.abspath(LOGS_DIR)}")
    
    print(f"\n🚆 GTFS Sources:")
    print(f"   Night train folders: {len(GTFS_NIGHT_FOLDERS)}")
    print(f"   Day train folders: {len(GTFS_DAY_FOLDERS)}")
    
    print(f"\n🌍 Country Mappings:")
    print(f"   Folder-level mappings: {len([v for v in NIGHT_FOLDER_COUNTRY_MAP.values() if v])} night, {len([v for v in DAY_FOLDER_COUNTRY_MAP.values() if v])} day")
    print(f"   Station-level mappings: {len(STATION_COUNTRY_MAP)}")
    
    print("=" * 70)

if __name__ == "__main__":
    # If run directly, show configuration and validate folders
    print_configuration()
    create_directories()
    validate_gtfs_folders()