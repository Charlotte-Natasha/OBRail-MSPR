"""
ObRail Europe ETL Project Setup
================================

Run this script to validate your project setup before running the pipeline.

Checks:
- Python version
- Dependencies (PySpark, Pandas, Java, odfpy)
- Folder structure
- GTFS data availability
- CO2 reference data
- Required scripts

Usage: python setup.py
"""

import os
import sys
import subprocess


def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


def print_step(step_num, title):
    print(f"\n{'─' * 70}")
    print(f"Step {step_num}: {title}")
    print('─' * 70)


def check_python_version():
    print_step(1, "Checking Python Version")
    version = sys.version_info
    print(f"   Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 8:
        print("   ✓ Python version is compatible (3.8+)")
        return True
    else:
        print("   ✗ Python 3.8+ required")
        return False


def check_dependencies():
    print_step(2, "Checking Dependencies")
    all_installed = True

    try:
        import pyspark
        print(f"   ✓ PySpark installed (version {pyspark.__version__})")
    except ImportError:
        print("   ✗ PySpark NOT installed")
        print("      Install with: pip install pyspark --break-system-packages")
        all_installed = False

    try:
        import pandas
        print(f"   ✓ Pandas installed (version {pandas.__version__})")
    except ImportError:
        print("   ✗ Pandas NOT installed")
        print("      Install with: pip install pandas --break-system-packages")
        all_installed = False

    try:
        import odf
        print("   ✓ odfpy installed (for ODS files)")
    except ImportError:
        print("   ⚠ odfpy NOT installed (needed for CO2 data)")
        print("      Install with: pip install odfpy --break-system-packages")

    try:
        import sqlalchemy
        print(f"   ✓ SQLAlchemy installed (version {sqlalchemy.__version__})")
    except ImportError:
        print("   ✗ SQLAlchemy NOT installed")
        print("      Install with: pip install sqlalchemy --break-system-packages")
        all_installed = False

    try:
        import dotenv
        print("   ✓ python-dotenv installed")
    except ImportError:
        print("   ✗ python-dotenv NOT installed")
        print("      Install with: pip install python-dotenv --break-system-packages")
        all_installed = False

    try:
        result = subprocess.run(
            ['java', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("   ✓ Java installed (required for PySpark)")
        else:
            print("   ⚠ Java check returned error")
            all_installed = False
    except FileNotFoundError:
        print("   ✗ Java NOT installed (required for PySpark)")
        print("      Install with: sudo apt-get install openjdk-11-jdk")
        all_installed = False
    except subprocess.TimeoutExpired:
        print("   ⚠ Java check timed out")

    return all_installed


def check_folder_structure():
    print_step(3, "Checking Folder Structure")

    required_folders = {
        "data/raw/night":    "Night train GTFS data",
        "data/raw/day":      "Day train GTFS data",
        "data/raw/co2":      "CO2 reference data (Back-on-Track ODS file)",
        "data/extracted":    "Extracted route data",
        "data/transformed":  "Cleaned and transformed data",
        "scripts":           "Python ETL scripts",
        "config":            "Configuration files",
        "logs":              "ETL execution logs (auto-created)",
    }

    all_exist = True
    for folder, description in required_folders.items():
        if os.path.exists(folder):
            print(f"   ✓ {folder}/ — {description}")
        else:
            print(f"   ✗ {folder}/ — MISSING")
            if folder != "logs":
                all_exist = False

    return all_exist


def check_required_files():
    print_step(4, "Checking Required Scripts")

    required_files = {
        "main.py":                      "Main pipeline orchestrator",
        "setup.py":                     "Project setup validator",
        "config/settings.py":           "Configuration settings",
        "scripts/night_trains.py":      "Night routes extraction",
        "scripts/day_trains.py":        "Day routes extraction",
        "scripts/clean_routes.py":      "Routes transformation and cleaning",
        "scripts/emissions.py":         "CO2 emissions extraction",
        "scripts/calculate_co2.py":     "Environmental impact calculation",
        "scripts/load_database.py":     "Database loading",
    }

    all_exist = True
    for filepath, description in required_files.items():
        if os.path.exists(filepath):
            print(f"   ✓ {filepath} — {description}")
        else:
            print(f"   ✗ {filepath} — MISSING")
            all_exist = False

    return all_exist


def scan_gtfs_data():
    print_step(5, "Scanning for GTFS Data")

    night_folder = "data/raw/night"
    day_folder = "data/raw/day"

    def scan_folder(folder, train_type):
        if not os.path.exists(folder):
            print(f"   ⚠ {train_type} folder not found: {folder}")
            return 0

        subfolders = [
            f for f in os.listdir(folder)
            if os.path.isdir(os.path.join(folder, f)) and not f.startswith('.')
        ]

        if not subfolders:
            print(f"   ⚠ No {train_type} GTFS folders found in {folder}/")
            return 0

        print(f"\n   {train_type.upper()} TRAINS:")
        valid_count = 0

        for subfolder in subfolders:
            path = os.path.join(folder, subfolder)
            files = os.listdir(path)
            gtfs_files = [f for f in files if f.endswith('.txt')]

            if not gtfs_files:
                print(f"      ✗ {subfolder}/ — NO GTFS FILES")
                continue

            required = ['stops.txt', 'trips.txt', 'routes.txt']
            has_required = all(f in gtfs_files for f in required)
            has_stop_times = 'stop_times.txt' in gtfs_files

            if has_required:
                status = "✓" if has_stop_times else "⚠"
                note = "" if has_stop_times else " (missing stop_times.txt — OK)"
                print(f"      {status} {subfolder}/ — {len(gtfs_files)} files{note}")
                valid_count += 1
            else:
                missing = [f for f in required if f not in gtfs_files]
                print(f"      ✗ {subfolder}/ — MISSING: {', '.join(missing)}")

        return valid_count

    night_count = scan_folder(night_folder, "night")
    day_count = scan_folder(day_folder, "day")
    total = night_count + day_count
    print(f"\n   Summary: {total} valid GTFS folders found")
    return total > 0


def check_co2_data():
    print_step(6, "Checking CO2 Reference Data")

    co2_folder = "data/raw/co2"
    co2_file = "data/raw/co2/Emissions.ods"

    if os.path.exists(co2_file):
        size_mb = os.path.getsize(co2_file) / (1024 * 1024)
        print(f"   ✓ {co2_file} — CO2 emission factors ({size_mb:.2f} MB)")
        print(f"      Source: Back-on-Track 2022")
        return True
    elif os.path.exists(co2_folder):
        files = os.listdir(co2_folder)
        if files:
            print(f"   ⚠ CO2 folder exists but Emissions.ods not found")
            print(f"      Files found: {', '.join(files)}")
        else:
            print(f"   ⚠ {co2_folder}/ exists but is empty")
        return False
    else:
        print(f"   ✗ {co2_folder}/ — NOT FOUND")
        print(f"      Place Emissions.ods (Back-on-Track data) in this folder")
        return False


def provide_instructions():
    print_step(7, "Next Steps")
    print("""
    1  If GTFS data is missing:
        - Download GTFS files from OpenMobilityData.org or national operators
        - Unzip into data/raw/night/ or data/raw/day/
        - Each source should be in its own subfolder

    2  If CO2 data is missing:
        - Download: 220915_B-o-T_GW_reduction_potential_data.ods
        - Source: Back-on-Track (European night trains database)
        - Rename to: Emissions.ods
        - Place in: data/raw/co2/

    3  Review configuration:
        - Open config/settings.py
        - Verify GTFS folder paths match your data

    4  Run the ETL pipeline:
        python main.py

    5  Check the results:
        - data/extracted/       Raw route extracts
        - data/transformed/     Cleaned data with CO2 calculations
        - logs/                 Execution logs per script
    """)


def main():
    print_header("ObRail Europe ETL — Project Setup Validation")
    print("Validates your environment before running the ETL pipeline.\n")

    checks = {
        "Python version":    check_python_version(),
        "Dependencies":      check_dependencies(),
        "Folder structure":  check_folder_structure(),
        "Required scripts":  check_required_files(),
        "GTFS data":         scan_gtfs_data(),
        "CO2 reference data": check_co2_data(),
    }

    provide_instructions()

    print_header("Setup Validation Summary")
    print("Checklist:\n")
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")

    all_passed = all(checks.values())
    print("\n" + "─" * 70)

    if all_passed:
        print("\n✅ All checks passed — ready to run the pipeline.")
        print("\n   Run: python main.py")
    else:
        print("\n⚠️  Some checks failed. Fix the issues above then run setup.py again.")

    print("\n" + "=" * 70 + "\n")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())