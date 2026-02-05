"""
ObRail Europe ETL Pipeline - Main Orchestrator
===============================================

This is the MAIN script that runs the entire ETL pipeline.

Run this with: python main.py

It will automatically:
1. Extract night routes
2. Extract day routes
3. Transform and clean all data
4. Generate summary report

Author: ObRail Europe Data Team
"""

import os
import sys
import time
from datetime import datetime

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")

def print_phase_separator():
    """Print a phase separator"""
    print("\n" + "-" * 80 + "\n")


# PHASE 1: EXTRACT

def run_extraction_phase():
    print_header("PHASE 1: EXTRACT - Extracting Routes from GTFS Data")
    start_time = time.time()

    print("🌙 Extracting NIGHT routes...")
    try:
        from scripts import night_trains
        night_trains.main()
        print("✓ Night routes extraction completed")
    except Exception as e:
        print(f"✗ Error extracting night routes: {str(e)}")
        return False

    print_phase_separator()

    print("☀️  Extracting DAY routes...")
    try:
        from scripts import day_trains   # FIXED NAME
        day_trains.main()
        print("✓ Day routes extraction completed")
    except Exception as e:
        print(f"✗ Error extracting day routes: {str(e)}")
        return False

    print(f"\n✅ EXTRACTION phase completed in {time.time() - start_time:.2f} seconds")
    return True


# PHASE 2: TRANSFORM

def run_transformation_phase():
    print_header("PHASE 2: TRANSFORM - Cleaning and Standardizing Data")
    start_time = time.time()

    print("🔄 Transforming and cleaning data...")
    try:
        from scripts import clean_routes
        clean_routes.main()
        print("✓ Data transformation completed")
    except Exception as e:
        print(f"✗ Error during transformation: {str(e)}")
        return False

    print(f"\n✅ TRANSFORMATION phase completed in {time.time() - start_time:.2f} seconds")
    return True


# PHASE 3: LOAD (Future)

def run_loading_phase():
    """Execute the loading phase - placeholder for future implementation"""
    print_header("PHASE 3: LOAD - Loading Data into Database")
    
    print("📊 Loading phase:")
    print("   Status: TO BE IMPLEMENTED")
    print("   This phase will load cleaned data into PostgreSQL database")
    print("")
    
    return True


# GENERATE SUMMARY REPORT

def generate_summary_report():
    """Generate a summary report of the ETL process"""
    print_header("ETL PIPELINE SUMMARY")

    extracted_dir = os.path.join("data", "extracted")
    transformed_dir = os.path.join("data", "transformed")

    print("📁 OUTPUT FILES:\n")

    
    # Extracted files
    
    extracted_files = [
        "day_routes.csv",
        "night_routes.csv"
    ]

    print("📦 Extracted data:")
    for filename in extracted_files:
        path = os.path.join(extracted_dir, filename)
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            print(f"   ✓ {path} ({size:.1f} KB)")
        else:
            print(f"   ✗ {path} - NOT FOUND")

    print()

    
    # Transformed files
    
    transformed_files = [
        "day_routes_cleaned.csv",
        "night_routes_cleaned.csv",
        "all_routes_cleaned.csv",
        "emissions_reference.csv",
        "emissions_summary.csv"
    ]

    print("🔧 Transformed data:")
    for filename in transformed_files:
        path = os.path.join(transformed_dir, filename)
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            print(f"   ✓ {path} ({size:.1f} KB)")
        else:
            print(f"   ✗ {path} - NOT FOUND")

    print("\n👉 Final output should be:")
    print(f"   {os.path.join(transformed_dir, 'all_routes_cleaned.csv')}\n")


# MAIN PIPELINE ORCHESTRATOR

def main():
    """Main ETL pipeline orchestrator"""
    
    print("\n" + "=" * 80)
    print("   ___  _    ___       _ _   _____ _____ _    ")
    print("  / _ \\| |_ | _ \\ __ _(_) | | __  |_   _| |   ")
    print(" | (_) | __ |   / / _` | | | | _|   | | | |__ ")
    print("  \\___/|_|_||_|_\\ \\__,_|_|_| |___   |_| |____|")
    print("")
    print("         European Rail Routes ETL Pipeline")
    print("=" * 80)
    
    start_time = time.time()
    
    print(f"\n🚀 Starting ETL Pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Phase 1: Extract
    if not run_extraction_phase():
        print("\n❌ ETL Pipeline FAILED at EXTRACTION phase")
        sys.exit(1)
    
    # Phase 2: Transform
    if not run_transformation_phase():
        print("\n❌ ETL Pipeline FAILED at TRANSFORMATION phase")
        sys.exit(1)
    
    # Phase 3: Load (placeholder)
    if not run_loading_phase():
        print("\n❌ ETL Pipeline FAILED at LOADING phase")
        sys.exit(1)
    
    # Generate summary
    generate_summary_report()
    
    # Final summary
    total_elapsed = time.time() - start_time
    
    print_header("ETL PIPELINE COMPLETE")
    print(f"✅ All phases completed successfully!")
    print(f"⏱️  Total execution time: {total_elapsed:.2f} seconds ({total_elapsed/60:.1f} minutes)")
    print(f"📁 Outputs:")
    print(f"   - Extracted data: data/extracted/")
    print(f"   - Transformed data: data/transformed/")
    print(f"   - Final output: data/transformed/all_routes_cleaned.csv")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)