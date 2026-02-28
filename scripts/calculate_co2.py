"""
Route Environmental Impact Calculator
======================================

Combines route data with CO2 emission factors to calculate
environmental impact of train vs plane travel.

Inputs:
- data/transformed/all_routes_cleaned.csv
- data/transformed/emissions_reference.csv

Output:
- data/transformed/environmental_impact.csv

Author: ObRail Europe Data Team
"""

import pandas as pd
import os
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
        logging.FileHandler("logs/calculate_co2.log")
    ]
)
logger = logging.getLogger("calculate_co2")

# ============================================
# CONFIGURATION
# ============================================

ROUTES_FILE = "data/transformed/all_routes_cleaned.csv"
CO2_REFERENCE_FILE = "data/transformed/emissions_reference.csv"
OUTPUT_FILE = "data/transformed/environmental_impact.csv"

# Default emission factors (g CO2 per passenger-km)
# Used as fallback if emissions_reference.csv cannot be read
# Source: Back-on-Track 2022 / ICCT
DEFAULT_EMISSION_FACTORS = {
    'train': 14,
    'plane': 144,
    'car': 132
}


# ============================================
# FUNCTION: Load emission factors
# ============================================

def load_emission_factors(file_path):
    """
    Load CO2 emission factors from reference file.
    Falls back to DEFAULT_EMISSION_FACTORS if file cannot be read.
    """
    logger.info(f"Loading CO2 emission factors from {file_path}")

    try:
        df = pd.read_csv(file_path)
        factors = {}

        train_row = df[df['transport_mode'].str.contains('Night Train', case=False, na=False)]
        if not train_row.empty:
            factors['train'] = train_row['gco2_per_pkm'].values[0]

        plane_row = df[df['transport_mode'] == 'Plane']
        if not plane_row.empty:
            factors['plane'] = plane_row['gco2_per_pkm'].values[0]

        car_row = df[df['transport_mode'].str.contains('Car', case=False, na=False)]
        if not car_row.empty:
            factors['car'] = car_row['gco2_per_pkm'].values[0]

        logger.info(f"Emission factors loaded — Train: {factors.get('train')} | Plane: {factors.get('plane')} | Car: {factors.get('car')} gCO2/pkm")
        return factors

    except Exception as e:
        logger.warning(f"Could not load {file_path}: {e} — using default emission factors")
        logger.info(f"Default factors — Train: {DEFAULT_EMISSION_FACTORS['train']} | Plane: {DEFAULT_EMISSION_FACTORS['plane']} | Car: {DEFAULT_EMISSION_FACTORS['car']} gCO2/pkm")
        return DEFAULT_EMISSION_FACTORS


# ============================================
# FUNCTION: Calculate route emissions
# ============================================

def calculate_route_emissions(routes_df, emission_factors):
    """
    Calculate CO2 emissions for each route.
    Formula: distance (km) × emission factor (g/pkm) ÷ 1000 = kg CO2
    """
    logger.info(f"Calculating environmental impact for {len(routes_df)} routes")

    df = routes_df.copy()

    train_factor = emission_factors.get('train', DEFAULT_EMISSION_FACTORS['train'])
    plane_factor = emission_factors.get('plane', DEFAULT_EMISSION_FACTORS['plane'])

    df['train_gco2_pkm'] = train_factor
    df['plane_gco2_pkm'] = plane_factor

    df['train_co2_kg'] = (df['distance_km'] * train_factor / 1000).round(2)
    df['plane_co2_kg'] = (df['distance_km'] * plane_factor / 1000).round(2)

    df['co2_savings_kg'] = (df['plane_co2_kg'] - df['train_co2_kg']).round(2)
    df['savings_percent'] = ((df['co2_savings_kg'] / df['plane_co2_kg']) * 100).round(1)

    df['emission_source'] = 'Back-on-Track 2022'
    df['calculation_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')

    logger.info(f"Emissions calculated — total CO2 savings: {df['co2_savings_kg'].sum():,.2f} kg ({df['co2_savings_kg'].sum()/1000:,.2f} t)")
    return df


# ============================================
# FUNCTION: Generate summary statistics
# ============================================

def generate_summary_statistics(df):
    """Log summary statistics about environmental impact"""
    total_routes = len(df)
    total_savings = df['co2_savings_kg'].sum()
    avg_savings = total_savings / total_routes

    logger.info(f"Summary — {total_routes} routes | total savings: {total_savings:,.2f} kg | avg per route: {avg_savings:,.2f} kg")

    # Top 10 routes by CO2 savings
    top_routes = df.nlargest(10, 'co2_savings_kg')[
        ['origin', 'destination', 'origin_country', 'destination_country',
         'distance_km', 'co2_savings_kg']
    ]
    logger.info(f"Top 10 routes by CO2 savings:\n{top_routes.to_string(index=False)}")

    # Country breakdown
    country_summary = df.groupby('origin_country').agg(
        route_count=('origin', 'count'),
        co2_savings_tons=('co2_savings_kg', lambda x: round(x.sum() / 1000, 2))
    ).sort_values('co2_savings_tons', ascending=False)
    logger.info(f"CO2 savings by country:\n{country_summary.head(10).to_string()}")

    # By train type — depends on 'type' column added by clean_routes.py
    if 'type' in df.columns:
        type_summary = df.groupby('type').agg(
            route_count=('origin', 'count'),
            co2_savings_tons=('co2_savings_kg', lambda x: round(x.sum() / 1000, 2))
        )
        logger.info(f"CO2 savings by train type:\n{type_summary.to_string()}")


# ============================================
# MAIN
# ============================================

def main():
    logger.info("Starting route environmental impact calculation")

    if not os.path.exists(ROUTES_FILE):
        logger.error(f"Routes file not found: {ROUTES_FILE} — run clean_routes.py first")
        return

    if not os.path.exists(CO2_REFERENCE_FILE):
        logger.warning(f"CO2 reference file not found: {CO2_REFERENCE_FILE} — will use default factors")

    try:
        # 1. Load emission factors
        emission_factors = load_emission_factors(CO2_REFERENCE_FILE)

        # 2. Load routes
        routes_df = pd.read_csv(ROUTES_FILE)
        logger.info(f"Loaded {len(routes_df)} routes from {ROUTES_FILE}")

        if 'distance_km' not in routes_df.columns:
            logger.error(f"'distance_km' column not found — available: {list(routes_df.columns)}")
            return

        # 3. Calculate emissions
        routes_with_co2 = calculate_route_emissions(routes_df, emission_factors)

        # 4. Save results
        output_dir = os.path.dirname(OUTPUT_FILE)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        routes_with_co2.to_csv(OUTPUT_FILE, index=False)
        logger.info(f"Saved: {OUTPUT_FILE}")

        # 5. Summary statistics
        generate_summary_statistics(routes_with_co2)

        logger.info("Environmental impact calculation complete")

    except Exception as e:
        logger.error(f"Calculation failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()