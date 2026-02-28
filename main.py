"""
ObRail Europe ETL Pipeline - Main Orchestrator
===============================================

Run the entire ETL pipeline with: python main.py

Phases:
1. Extract night routes (night_trains.py)
2. Extract day routes (day_trains.py)
3. Extract CO2 reference data (emissions.py)
4. Transform and clean routes (clean_routes.py)
5. Calculate environmental impact (calculate_co2.py)
6. Load into PostgreSQL (load_database.py)

Author: ObRail Europe Data Team
"""

import os
import sys
import time
import logging
from datetime import datetime

# ============================================
# LOGGING SETUP
# ============================================

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler()  # also print to terminal
    ]
)
logger = logging.getLogger("pipeline")


# ============================================
# HELPERS
# ============================================

def run_phase(phase_name, module_path, func_name="main"):
    """Run a single ETL phase and return True/False"""
    logger.info(f"Starting: {phase_name}")
    start_time = time.time()

    try:
        parts = module_path.split(".")
        module = __import__(module_path, fromlist=[parts[-1]])
        getattr(module, func_name)()
        elapsed = time.time() - start_time
        logger.info(f"Done: {phase_name} ({elapsed:.2f}s)")
        return True
    except Exception as e:
        logger.error(f"Failed: {phase_name} — {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# PHASES
# ============================================

def run_extraction_phase():
    logger.info("=== PHASE 1: EXTRACT ===")
    if not run_phase("Night routes extraction", "scripts.night_trains"):
        return False
    if not run_phase("Day routes extraction", "scripts.day_trains"):
        return False
    return True


def extract_co2_reference_data():
    logger.info("=== PHASE 2: CO2 REFERENCE ===")
    return run_phase("CO2 reference extraction", "scripts.emissions")


def run_transformation_phase():
    logger.info("=== PHASE 3: TRANSFORM ===")
    return run_phase("Routes cleaning and transformation", "scripts.clean_routes")


def calculate_environmental_impact():
    logger.info("=== PHASE 4: ENVIRONMENTAL IMPACT ===")
    return run_phase("Environmental impact calculation", "scripts.calculate_co2")


def run_loading_phase():
    logger.info("=== PHASE 5: LOAD ===")
    return run_phase("Database loading", "scripts.load_database")


# ============================================
# SUMMARY REPORT
# ============================================

def generate_summary_report():
    """Log file sizes and existence of all expected outputs"""
    logger.info("=== PIPELINE SUMMARY ===")

    expected_files = [
        "data/extracted/day_routes.csv",
        "data/extracted/night_routes.csv",
        "data/transformed/day_routes_cleaned.csv",
        "data/transformed/night_routes_cleaned.csv",
        "data/transformed/all_routes_cleaned.csv",
        "data/transformed/emissions_reference.csv",
        "data/transformed/emissions_summary.csv",
        "data/transformed/environmental_impact.csv",
    ]

    for path in expected_files:
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            logger.info(f"OK: {path} ({size_kb:.1f} KB)")
        else:
            logger.warning(f"MISSING: {path}")


# ============================================
# MAIN
# ============================================

def main():
    start_time = time.time()
    logger.info(f"ObRail Europe ETL pipeline started — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    phases = [
        ("Extraction",             run_extraction_phase),
        ("CO2 reference",          extract_co2_reference_data),
        ("Transformation",         run_transformation_phase),
        ("Environmental impact",   calculate_environmental_impact),
        ("Database loading",       run_loading_phase),
    ]

    for phase_name, phase_fn in phases:
        if not phase_fn():
            logger.error(f"Pipeline FAILED at: {phase_name}")
            sys.exit(1)

    generate_summary_report()

    total_elapsed = time.time() - start_time
    logger.info(f"Pipeline complete — {total_elapsed:.2f}s ({total_elapsed/60:.1f} min)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)