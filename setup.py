"""
ObRail Europe ETL Project Setup
================================

Run this script to validate your project setup.

This checks:
- Python version
- Dependencies (PySpark, Pandas, Java)
- Folder structure
- GTFS data availability
- CO2 reference data
- Configuration files

Usage: python setup.py
"""

import os
import sys
import subprocess

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")

def print_step(step_num, title):
    """Print step header"""
    print(f"\n{'─' * 70}")
    print(f"Step {step_num}: {title}")
    print('─' * 70)

def check_python_version():
    """Check if Python version is compatible"""
    print_step(1, "Checking Python Version")
    
    version = sys.version_info
    print(f"   Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("   ✓ Python version is compatible (3.8+)")
        return True
    else:
        print("   ✗ Python 3.8+ required")
        print("   Install newer Python version")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print_step(2, "Checking Dependencies")
    
    all_installed = True
    
    # Check PySpark
    try:
        import pyspark
        print(f"   ✓ PySpark installed (version {pyspark.__version__})")
    except ImportError:
        print("   ✗ PySpark NOT installed")
        print("      Install with: pip install pyspark --break-system-packages")
        all_installed = False
    
    # Check Pandas
    try:
        import pandas
        print(f"   ✓ Pandas installed (version {pandas.__version__})")
    except ImportError:
        print("   ✗ Pandas NOT installed")
        print("      Install with: pip install pandas --break-system-packages")
        all_installed = False
    
    # Check odfpy (for reading ODS files)
    try:
        import odf
        print(f"   ✓ odfpy installed (for ODS files)")
    except ImportError:
        print("   ⚠ odfpy NOT installed (needed for CO2 data)")
        print("      Install with: pip install odfpy --break-system-packages")
    
    # Check Java
    try:
        result = subprocess.run(['java', '-version'], 
                                capture_output=True, 
                                text=True, 
                                timeout=5)
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
    """Check if required folders exist"""
    print_step(3, "Checking Folder Structure")
    
    required_folders = {
        "data/raw/night": "Night train GTFS data",
        "data/raw/day": "Day train GTFS data",
        "data/raw/co2": "CO2 reference data (Back-on-Track ODS file)",
        "data/extracted": "Extracted route data",
        "data/transformed": "Cleaned and transformed data",
        "scripts": "Python scripts (extraction, transformation, emissions)",
        "config": "Configuration files",
        "logs": "ETL execution logs (optional)",
    }
    
    all_exist = True
    
    for folder, description in required_folders.items():
        if os.path.exists(folder):
            print(f"   ✓ {folder}/ - {description}")
        else:
            print(f"   ✗ {folder}/ - MISSING")
            # Don't fail for optional folders
            if folder not in ["logs"]:
                all_exist = False
    
    return all_exist

def check_required_files():
    """Check if required Python files exist"""
    print_step(4, "Checking Required Scripts")
    
    required_files = {
        "config/settings.py": "Configuration settings",
        "scripts/night_trains.py": "Night routes extraction",
        "scripts/day_trains.py": "Day routes extraction",
        "scripts/clean_routes.py": "Routes transformation and cleaning",
        "scripts/emissions.py": "CO2 emissions extraction",
        "scripts/calculate_co2.py": "Environmental impact calculation",
        "main.py": "Main pipeline orchestrator",
    }
    
    all_exist = True
    
    for filepath, description in required_files.items():
        if os.path.exists(filepath):
            print(f"   ✓ {filepath} - {description}")
        else:
            print(f"   ✗ {filepath} - MISSING")
            all_exist = False
    
    return all_exist

def scan_gtfs_data():
    """Scan for GTFS data"""
    print_step(5, "Scanning for GTFS Data")
    
    night_folder = "data/raw/night"
    day_folder = "data/raw/day"
    
    def scan_folder(folder, train_type):
        if not os.path.exists(folder):
            print(f"   ⚠ {train_type} folder not found: {folder}")
            return 0
        
        subfolders = [f for f in os.listdir(folder) 
                        if os.path.isdir(os.path.join(folder, f)) and not f.startswith('.')]
        
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
                print(f"      ✗ {subfolder}/ - NO GTFS FILES")
                continue
            
            # Check for required files
            required = ['stops.txt', 'trips.txt', 'routes.txt']
            has_required = all(f in gtfs_files for f in required)
            has_stop_times = 'stop_times.txt' in gtfs_files
            
            if has_required:
                status = "✓" if has_stop_times else "⚠"
                note = "" if has_stop_times else " (missing stop_times.txt - OK)"
                print(f"      {status} {subfolder}/ - {len(gtfs_files)} files{note}")
                valid_count += 1
            else:
                missing = [f for f in required if f not in gtfs_files]
                print(f"      ✗ {subfolder}/ - MISSING: {', '.join(missing)}")
        
        return valid_count
    
    night_count = scan_folder(night_folder, "night")
    day_count = scan_folder(day_folder, "day")
    
    total = night_count + day_count
    print(f"\n   📊 Summary: {total} valid GTFS folders found")
    
    return total > 0

def check_co2_data():
    """Check if CO2 reference data exists"""
    print_step(6, "Checking CO2 Reference Data")
    
    co2_folder = "data/raw/co2"
    co2_file = "data/raw/co2/Emissions.ods"
    
    if os.path.exists(co2_file):
        # Check file size
        size_mb = os.path.getsize(co2_file) / (1024 * 1024)
        print(f"   ✓ {co2_file} - CO2 emission factors ({size_mb:.2f} MB)")
        print(f"      Source: Back-on-Track 2022")
        return True
    elif os.path.exists(co2_folder):
        files = os.listdir(co2_folder)
        if files:
            print(f"   ⚠ CO2 folder exists but Emissions.ods not found")
            print(f"      Files in folder: {', '.join(files)}")
            print(f"      Expected: Emissions.ods (Back-on-Track data)")
        else:
            print(f"   ⚠ {co2_folder}/ exists but is empty")
        return False
    else:
        print(f"   ✗ {co2_folder}/ - NOT FOUND")
        print(f"      CO2 reference data is REQUIRED for environmental impact analysis")
        print(f"      Place 'Emissions.ods' (Back-on-Track data) in this folder")
        return False

def provide_instructions():
    """Provide next steps"""
    print_step(7, "Next Steps")
    
    print("""
    Your project setup is being validated. Here's what to do:

    1️⃣  If GTFS data is missing:
        - Download GTFS files from:
            * OpenMobilityData.org
            * National rail operators (SNCF, DB, ÖBB, SBB)
            * Back-on-Track database
        - Unzip into data/raw/night/ or data/raw/day/
        - Each source should be in its own subfolder

    2️⃣  If CO2 data is missing:
        - Download: 220915_B-o-T_GW_reduction_potential_data.ods
        - Source: Back-on-Track (European night trains database)
        - Rename to: Emissions.ods
        - Place in: data/raw/co2/

    3️⃣  Review configuration:
        - Open config/settings.py
        - Verify GTFS folder paths match your data
        - Update STATION_COUNTRY_MAP if needed

    4️⃣  Run the ETL pipeline:
        python scripts/main.py

    5️⃣  Check the results:
        - data/extracted/ → Raw route extracts
        - data/transformed/ → Cleaned data with CO2 calculations
        - data/transformed/all_routes_environmental_impact.csv → Final output

    📚 For more help:
        - README.md for detailed instructions
        - Check documentation files in project root
    """)

def main():
    """Main setup validation"""
    
    print_header("ObRail Europe ETL - Project Setup Validation")
    
    print("""
This script validates your project setup and checks if everything
is ready to run the ETL pipeline with environmental impact analysis.
    """)
    
    # Run all checks
    checks = {
        "Python version": check_python_version(),
        "Dependencies": check_dependencies(),
        "Folder structure": check_folder_structure(),
        "Required scripts": check_required_files(),
        "GTFS data": scan_gtfs_data(),
        "CO2 reference data": check_co2_data(),
    }
    
    # Provide instructions
    provide_instructions()
    
    # Final summary
    print_header("Setup Validation Summary")
    
    print("📋 Checklist:\n")
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
    
    all_passed = all(checks.values())
    
    print("\n" + "─" * 70)
    
    if all_passed:
        print("\n✅ All checks passed! You're ready to run the ETL pipeline.")
        print("\n   🚀 Run: python scripts/main.py")
        print("\n   This will:")
        print("      1. Extract routes from GTFS data")
        print("      2. Extract CO2 emission factors")
        print("      3. Clean and transform route data")
        print("      4. Calculate environmental impact per route")
        print("      5. Generate final output with CO2 savings")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("   Once fixed, run this setup script again to verify.")
        print("\n   📝 Common fixes:")
        print("      - Missing folders: Create them manually")
        print("      - Missing scripts: Download from project repository")
        print("      - Missing GTFS data: Download and unzip into data/raw/")
        print("      - Missing CO2 data: Download Emissions.ods from Back-on-Track")
    
    print("\n" + "=" * 70 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())