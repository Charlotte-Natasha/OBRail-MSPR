"""
ObRail Europe ETL Project Setup
================================

Run this script to validate your project setup.

This checks:
- Python version
- Dependencies (PySpark, Pandas, Java)
- Folder structure
- GTFS data availability
- Configuration

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
        print("   ⚠ Pandas NOT installed (optional but recommended)")
        print("      Install with: pip install pandas --break-system-packages")
    
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
        "data/extracted": "Extracted route data",
        "data/transformed": "Cleaned and transformed data",
        "scripts": "Extraction and transformation scripts",
        "config": "Configuration files",
    }
    
    all_exist = True
    
    for folder, description in required_folders.items():
        if os.path.exists(folder):
            print(f"   ✓ {folder}/ - {description}")
        else:
            print(f"   ✗ {folder}/ - MISSING")
            all_exist = False
    
    return all_exist

def check_required_files():
    """Check if required Python files exist"""
    print_step(4, "Checking Required Files")
    
    required_files = {
        "config/settings.py": "Configuration settings",
        "scripts/night_routes.py": "Night routes extraction",
        "scripts/day_routes.py": "Day routes extraction",
        "scripts/clean_routes.py": "Data transformation",
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

def provide_instructions():
    """Provide next steps"""
    print_step(6, "Next Steps")
    
    print("""
   Your project is set up! Here's what to do next:

   1️⃣  If GTFS data is missing:
      - Download GTFS files from sources
      - Unzip into data/raw/night/ or data/raw/day/
      - Each source gets its own subfolder

   2️⃣  Review configuration:
      - Open config/settings.py
      - Verify GTFS folder paths match your data
      - Check STATION_COUNTRY_MAP is comprehensive

     3️⃣  Run the ETL pipeline:
        python main.py

     4️⃣  Check the results:
        - Look in data/extracted/ for raw extracts
        - Look in data/transformed/ for cleaned data
        - Review logs for any errors

    📚 For more help:
        - README.md for detailed instructions
        - Check documentation files
    """)

def main():
    """Main setup validation"""
    
    print_header("ObRail Europe ETL - Project Setup Validation")
    
    print("""
This script validates your project setup and checks if everything
is ready to run the ETL pipeline.
    """)
    
    # Run all checks
    checks = {
        "Python version": check_python_version(),
        "Dependencies": check_dependencies(),
        "Folder structure": check_folder_structure(),
        "Required files": check_required_files(),
        "GTFS data": scan_gtfs_data(),
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
    
    if all_passed:
        print("\n✅ All checks passed! You're ready to run the ETL pipeline.")
        print("\n   Run: python main.py")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("   Once fixed, run this setup script again to verify.")
    
    print("\n" + "=" * 70 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())