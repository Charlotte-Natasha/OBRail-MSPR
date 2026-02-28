"""
Comprehensive Back-on-Track Data Extraction
============================================

Extracts multiple datasets from the Back-on-Track ODS file:
1. CO2 emissions by transport mode
2. Flight routes replaceable by trains
3. Summary statistics

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
        logging.FileHandler("logs/emissions.log")
    ]
)
logger = logging.getLogger("emissions")

# ============================================
# CONFIGURATION
# ============================================

INPUT_FILE = "data/raw/co2/Emissions.ods"
OUTPUT_DIR = "data/transformed/"


# ============================================
# FUNCTION 1: Extract CO2 emissions by mode
# ============================================

def extract_emissions_by_mode(file_path):
    """Extract CO2 emissions per transport mode from Back-on-Track ODS file"""
    logger.info("Extracting CO2 emissions by transport mode")

    df = pd.read_excel(file_path, sheet_name='GHGbyMeans', engine='odf')

    df_clean = df.iloc[:, 0:3].copy()
    df_clean.columns = ['transport_mode', 'gco2_per_pkm', 'gco2_per_pkm_rf3']

    df_clean = df_clean.dropna(subset=['transport_mode'])
    df_clean['transport_mode'] = df_clean['transport_mode'].str.replace('*', '', regex=False).str.strip()

    df_clean['gco2_per_pkm'] = pd.to_numeric(df_clean['gco2_per_pkm'], errors='coerce')
    df_clean['gco2_per_pkm_rf3'] = pd.to_numeric(df_clean['gco2_per_pkm_rf3'], errors='coerce')

    df_clean['source'] = 'Back-on-Track'
    df_clean['year'] = 2022

    logger.info(f"Extracted {len(df_clean)} transport modes")
    return df_clean


# ============================================
# FUNCTION 2: Extract flight routes (sample)
# ============================================

def extract_flight_routes(file_path, sample_size=100):
    """Extract sample of flight routes replaceable by trains"""
    logger.info(f"Extracting flight routes sample (n={sample_size})")

    df = pd.read_excel(file_path, sheet_name='Flights2019', engine='odf', skiprows=3)

    try:
        df_clean = df[['1stCity', '2ndCity', 'PAX', 'Distance', 'TrainTime',
                       'AviationEmissions', 'NightTrain']].copy()

        df_clean.columns = ['origin_city', 'destination_city', 'passengers_2019',
                            'distance_km', 'train_time_hours', 'aviation_emissions_tco2e',
                            'train_emissions_tco2e']

        df_clean = df_clean.dropna(subset=['origin_city', 'destination_city'])

        numeric_cols = ['passengers_2019', 'distance_km', 'train_time_hours',
                        'aviation_emissions_tco2e', 'train_emissions_tco2e']
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

        if 'aviation_emissions_tco2e' in df_clean.columns and 'train_emissions_tco2e' in df_clean.columns:
            df_clean['co2_savings_tco2e'] = (
                df_clean['aviation_emissions_tco2e'] - df_clean['train_emissions_tco2e']
            )

        df_sample = df_clean.head(sample_size)
        logger.info(f"Extracted {len(df_sample)} flight routes")
        return df_sample

    except Exception as e:
        logger.warning(f"Could not extract flight routes: {str(e)} — skipping")
        return pd.DataFrame()


# ============================================
# FUNCTION 3: Create summary statistics
# ============================================

def create_summary_statistics(emissions_df):
    """Create summary statistics comparing transport modes against plane and car"""
    logger.info("Creating summary statistics")

    summary = {
        'transport_mode': [],
        'gco2_per_pkm': [],
        'vs_plane_savings_percent': [],
        'vs_car_savings_percent': []
    }

    plane_emissions = emissions_df[
        emissions_df['transport_mode'].str.contains('Plane', na=False)
    ]['gco2_per_pkm'].values

    car_emissions = emissions_df[
        emissions_df['transport_mode'].str.contains('Car', na=False)
    ]['gco2_per_pkm'].values

    plane_baseline = plane_emissions[0] if len(plane_emissions) > 0 else None
    car_baseline = car_emissions[0] if len(car_emissions) > 0 else None

    for _, row in emissions_df.iterrows():
        mode = row['transport_mode']
        emissions = row['gco2_per_pkm']

        if pd.notna(emissions):
            summary['transport_mode'].append(mode)
            summary['gco2_per_pkm'].append(emissions)

            if plane_baseline:
                savings = ((plane_baseline - emissions) / plane_baseline) * 100
                summary['vs_plane_savings_percent'].append(round(savings, 1))
            else:
                summary['vs_plane_savings_percent'].append(None)

            if car_baseline:
                savings = ((car_baseline - emissions) / car_baseline) * 100
                summary['vs_car_savings_percent'].append(round(savings, 1))
            else:
                summary['vs_car_savings_percent'].append(None)

    summary_df = pd.DataFrame(summary)
    logger.info(f"Summary statistics created for {len(summary_df)} transport modes")
    return summary_df


# ============================================
# MAIN
# ============================================

def main():
    logger.info("Starting Back-on-Track data extraction")

    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}")
        logger.error("Place Emissions.ods in data/raw/co2/ and run again")
        return

    logger.info(f"Found input file: {INPUT_FILE}")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created output directory: {OUTPUT_DIR}")

    try:
        # 1. Extract emissions by mode
        emissions_df = extract_emissions_by_mode(INPUT_FILE)
        emissions_file = os.path.join(OUTPUT_DIR, "emissions_reference.csv")
        emissions_df.to_csv(emissions_file, index=False)
        logger.info(f"Saved: {emissions_file}")

        # 2. Create and save summary statistics
        summary_df = create_summary_statistics(emissions_df)
        summary_file = os.path.join(OUTPUT_DIR, "emissions_summary.csv")
        summary_df.to_csv(summary_file, index=False)
        logger.info(f"Saved: {summary_file}")

        # 3. Extract flight routes (optional)
        try:
            routes_df = extract_flight_routes(INPUT_FILE, sample_size=50)
            if not routes_df.empty:
                routes_file = os.path.join(OUTPUT_DIR, "replaceable_flight_routes_sample.csv")
                routes_df.to_csv(routes_file, index=False)
                logger.info(f"Saved: {routes_file}")
        except Exception as e:
            logger.warning(f"Skipping flight routes extraction: {str(e)}")

        # 4. Log key findings
        train_row = emissions_df[emissions_df['transport_mode'].str.contains('Night Train', na=False)]
        plane_row = emissions_df[emissions_df['transport_mode'].str.contains('Plane', na=False, regex=False)]

        if not train_row.empty and not plane_row.empty:
            train_em = train_row['gco2_per_pkm'].values[0]
            plane_em = plane_row['gco2_per_pkm'].values[0]
            savings = ((plane_em - train_em) / plane_em) * 100
            logger.info(f"Night Train: {train_em} gCO2/pkm | Airplane: {plane_em} gCO2/pkm | Savings: {savings:.1f}%")

        logger.info("Back-on-Track extraction complete")

    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()