"""
ETL Configuration File
======================

Central configuration for all ETL scripts.
Modify paths here to match your folder structure.
"""

import os

# ============================================
# PROJECT STRUCTURE
# ============================================

# Set to True if scripts are in scripts/ subfolder, False if in project root
SCRIPTS_IN_SUBFOLDER = False

BASE_PATH = "../" if SCRIPTS_IN_SUBFOLDER else ""

# ============================================
# DIRECTORY PATHS
# ============================================

RAW_DATA_DIR       = os.path.join(BASE_PATH, "data/raw/")
RAW_NIGHT_DIR      = os.path.join(RAW_DATA_DIR, "night/")
RAW_DAY_DIR        = os.path.join(RAW_DATA_DIR, "day/")
RAW_EMISSIONS_DIR  = os.path.join(RAW_DATA_DIR, "co2/")
EXTRACTED_DIR      = os.path.join(BASE_PATH, "data/extracted/")
TRANSFORMED_DIR    = os.path.join(BASE_PATH, "data/transformed/")
LOGS_DIR           = os.path.join(BASE_PATH, "logs/")

# ============================================
# GTFS SOURCE FOLDERS
# ============================================

GTFS_NIGHT_FOLDERS = [
    os.path.join(RAW_NIGHT_DIR, "Switzerland/"),
    os.path.join(RAW_NIGHT_DIR, "long_distance/"),
    os.path.join(RAW_NIGHT_DIR, "sncf-data/"),
    os.path.join(RAW_NIGHT_DIR, "open_data/"),
    os.path.join(RAW_NIGHT_DIR, "long_distance_rail/"),
]

GTFS_DAY_FOLDERS = [
    os.path.join(RAW_DAY_DIR, "Denmark/"),
    os.path.join(RAW_DAY_DIR, "Eurostar_international/"),
    os.path.join(RAW_DAY_DIR, "France/"),
    os.path.join(RAW_DAY_DIR, "Germany/"),
    os.path.join(RAW_DAY_DIR, "Switzerland/"),
]

# ============================================
# OUTPUT FILE PATHS
# ============================================

NIGHT_ROUTES_EXTRACTED      = os.path.join(EXTRACTED_DIR,   "night_routes.csv")
DAY_ROUTES_EXTRACTED        = os.path.join(EXTRACTED_DIR,   "day_routes.csv")
NIGHT_ROUTES_CLEANED        = os.path.join(TRANSFORMED_DIR, "night_routes_cleaned.csv")
DAY_ROUTES_CLEANED          = os.path.join(TRANSFORMED_DIR, "day_routes_cleaned.csv")
ALL_ROUTES_CLEANED          = os.path.join(TRANSFORMED_DIR, "all_routes_cleaned.csv")
CO2_EMISSIONS_REFERENCE     = os.path.join(TRANSFORMED_DIR, "emissions_reference.csv")
CO2_EMISSIONS_SUMMARY       = os.path.join(TRANSFORMED_DIR, "emissions_summary.csv")
ROUTES_ENVIRONMENTAL_IMPACT = os.path.join(TRANSFORMED_DIR, "environmental_impact.csv")

# ============================================
# EMISSION FACTORS
# Source: Back-on-Track 2022 / ICCT
# ============================================

EMISSION_FACTORS = {
    'train':     14,   # Night/day trains (gCO2/pkm)
    'plane':    144,   # Airplane without radiative forcing
    'plane_rf': 389,   # Airplane with radiative forcing (x3.0)
    'car':      132,   # Large car (diesel)
    'coach':     22,   # Coach/bus
}

# ============================================
# COUNTRY MAPPING
# ============================================

NIGHT_FOLDER_COUNTRY_MAP = {
    os.path.join(RAW_NIGHT_DIR, "Switzerland/"):       "CH",
    os.path.join(RAW_NIGHT_DIR, "long_distance/"):     None,
    os.path.join(RAW_NIGHT_DIR, "sncf-data/"):         "FR",
    os.path.join(RAW_NIGHT_DIR, "open_data/"):         None,
    os.path.join(RAW_NIGHT_DIR, "long_distance_rail/"): None,
}

DAY_FOLDER_COUNTRY_MAP = {
    os.path.join(RAW_DAY_DIR, "Denmark/"):              "DK",
    os.path.join(RAW_DAY_DIR, "Eurostar_international/"): None,
    os.path.join(RAW_DAY_DIR, "France/"):               "FR",
    os.path.join(RAW_DAY_DIR, "Germany/"):              "DE",
    os.path.join(RAW_DAY_DIR, "Switzerland/"):          "CH",
}

STATION_COUNTRY_MAP = {
    # Switzerland
    "basel": "CH", "zurich": "CH", "brig": "CH", "lausanne": "CH",
    "geneve": "CH", "geneva": "CH", "montreux": "CH", "olten": "CH",
    "liestal": "CH",
    # Italy
    "como": "IT", "chiasso": "IT", "lugano": "IT", "bellinzona": "IT",
    "domodossola": "IT", "simplontunnel": "IT", "milano": "IT", "milan": "IT",
    "roma": "IT", "rome": "IT",
    # France
    "paris nord": "FR", "paris gare du nord": "FR", "lyon": "FR",
    "marseille": "FR", "nice": "FR", "lille europe": "FR",
    "calais ville": "FR", "dunkerque": "FR", "marne la vallee": "FR",
    "bourg st maurice": "FR",
    # Belgium
    "bruxelles midi": "BE", "brussels midi": "BE",
    # Netherlands
    "amsterdam centraal": "NL", "rotterdam centraal": "NL",
    # Austria
    "wien": "AT", "vienna": "AT", "salzburg": "AT", "innsbruck": "AT", "graz": "AT",
    # Germany
    "munchen": "DE", "munich": "DE", "berlin": "DE", "hamburg": "DE",
    "koln": "DE", "cologne": "DE", "frankfurt": "DE", "dortmund": "DE", "essen": "DE",
    # United Kingdom
    "st pancras international": "GB", "london st pancras": "GB",
    # Czech Republic
    "prague": "CZ", "praha": "CZ",
    # Hungary
    "budapest": "HU",
}

# ============================================
# PYSPARK
# ============================================

SPARK_APP_NAME          = "ObRail_ETL_Pipeline"
SPARK_DRIVER_MEMORY     = "4g"
SPARK_SHUFFLE_PARTITIONS = "10"

# ============================================
# HELPER FUNCTIONS
# ============================================

def create_directories():
    """Create all necessary output directories if they don't exist"""
    for directory in [EXTRACTED_DIR, TRANSFORMED_DIR, LOGS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")


def get_actual_gtfs_folders(folder_type="both"):
    """Return only GTFS folders that actually exist on disk"""
    if folder_type == "night":
        folders = GTFS_NIGHT_FOLDERS
    elif folder_type == "day":
        folders = GTFS_DAY_FOLDERS
    else:
        folders = GTFS_NIGHT_FOLDERS + GTFS_DAY_FOLDERS
    return [f for f in folders if os.path.exists(f)]


def validate_gtfs_folders():
    """Print which GTFS folders exist and have data"""
    print("\nValidating GTFS folder structure...")
    all_folders = GTFS_NIGHT_FOLDERS + GTFS_DAY_FOLDERS
    existing, missing = [], []

    for folder in all_folders:
        if os.path.exists(folder):
            gtfs_files = [f for f in os.listdir(folder) if f.endswith('.txt')]
            if gtfs_files:
                existing.append(folder)
                print(f"   ✓ {folder} ({len(gtfs_files)} .txt files)")
            else:
                missing.append(folder)
                print(f"   ⚠ {folder} (empty)")
        else:
            missing.append(folder)
            print(f"   ✗ {folder} (not found)")

    print(f"\n   {len(existing)} valid, {len(missing)} missing/empty")
    return existing, missing


def print_configuration():
    """Print current configuration summary"""
    print("=" * 70)
    print("ETL PIPELINE CONFIGURATION")
    print("=" * 70)
    print(f"\nBase path:        {os.path.abspath(BASE_PATH)}")
    print(f"Raw data:         {os.path.abspath(RAW_DATA_DIR)}")
    print(f"Extracted:        {os.path.abspath(EXTRACTED_DIR)}")
    print(f"Transformed:      {os.path.abspath(TRANSFORMED_DIR)}")
    print(f"Logs:             {os.path.abspath(LOGS_DIR)}")
    print(f"Night folders:    {len(GTFS_NIGHT_FOLDERS)}")
    print(f"Day folders:      {len(GTFS_DAY_FOLDERS)}")
    print(f"Station mappings: {len(STATION_COUNTRY_MAP)}")
    print("=" * 70)


if __name__ == "__main__":
    print_configuration()
    create_directories()
    validate_gtfs_folders()