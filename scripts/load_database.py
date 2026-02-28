"""
ObRail Europe - Database Loading Script
========================================

Loads transformed route data with environmental impact into PostgreSQL.

This script:
1. Connects to PostgreSQL using SQLAlchemy
2. Verifies the database schema was created correctly
3. Loads CSV data from the transformation phase
4. Inserts data into dimension and fact tables
5. Validates the loaded data

Author: ObRail Europe Data Team
Version: 2.0
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime
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
        logging.FileHandler("logs/load_database.log")
    ]
)
logger = logging.getLogger("load_database")

# ============================================
# CONFIGURATION
# ============================================

load_dotenv()

# Input CSV — resolved inside main() to avoid module-level side effects
PRIMARY_CSV = "data/transformed/environmental_impact.csv"
FALLBACK_CSV = "data/transformed/all_routes_environmental_impact.csv"

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f"postgresql://{os.getenv('POSTGRES_USER', 'obrail_user')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'password')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5433')}/"
    f"{os.getenv('POSTGRES_DB', 'obrail_db')}"
)


# ============================================
# FUNCTION: Connect to Database
# ============================================

def connect_database():
    """Connect to PostgreSQL using SQLAlchemy"""
    logger.info("Connecting to PostgreSQL database")

    safe_url = DATABASE_URL.replace(os.getenv('POSTGRES_PASSWORD', ''), '****')
    logger.info(f"Using: {safe_url}")

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return engine
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        logger.error("Check: docker ps | docker compose up -d | .env credentials")
        return None


# ============================================
# FUNCTION: Verify Database Schema
# ============================================

def verify_schema(engine):
    """Verify required tables exist"""
    logger.info("Verifying database schema")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")

        required_tables = ['dim_countries', 'dim_transport_modes', 'fact_routes']
        missing = [t for t in required_tables if t not in tables]

        if missing:
            logger.error(f"Missing tables: {', '.join(missing)}")
            logger.error("Reset Docker: docker compose down -v && docker compose up -d")
            return False

        logger.info("All required tables exist")
        return True


# ============================================
# FUNCTION: Load CSV Data
# ============================================

def load_csv_data(input_csv):
    """Load the transformed CSV file"""
    logger.info(f"Loading CSV data from {input_csv}")

    if not os.path.exists(input_csv):
        logger.error(f"File not found: {input_csv} — run calculate_co2.py first")
        return None

    try:
        df = pd.read_csv(input_csv)
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}")
        return None


# ============================================
# FUNCTION: Prepare Data
# ============================================

def prepare_data(df):
    """Map CSV columns to database schema and clean data"""
    logger.info("Preparing data for database insertion")

    df_clean = pd.DataFrame()

    df_clean['route_name'] = df.get('route_name', df.get('route_name_simple'))
    df_clean['route_name_simple'] = df.get('route_name_simple', df.get('route_name'))
    df_clean['origin'] = df['origin']
    df_clean['destination'] = df['destination']
    df_clean['origin_country'] = df['origin_country']
    df_clean['destination_country'] = df['destination_country']
    df_clean['distance_km'] = df['distance_km']
    df_clean['service_type'] = df.get('service_type', df.get('type'))
    df_clean['train_type'] = df.get('type', df.get('service_type'))
    df_clean['train_gco2_pkm'] = df.get('train_gco2_pkm', 14)
    df_clean['plane_gco2_pkm'] = df.get('plane_gco2_pkm', 144)
    df_clean['train_co2_kg'] = df['train_co2_kg']
    df_clean['plane_co2_kg'] = df['plane_co2_kg']
    df_clean['co2_savings_kg'] = df['co2_savings_kg']
    df_clean['savings_percent'] = df['savings_percent']
    df_clean['emission_source'] = df.get('emission_source', 'Back-on-Track 2022')
    df_clean['calculation_date'] = pd.to_datetime(
        df.get('calculation_date', datetime.now().date())
    )

    before_count = len(df_clean)
    df_clean = df_clean.dropna(subset=['origin', 'destination', 'distance_km'])
    after_count = len(df_clean)

    removed = before_count - after_count
    if removed > 0:
        logger.warning(f"Removed {removed} rows with NULL critical values")

    logger.info(f"Prepared {after_count} valid rows")
    return df_clean


# ============================================
# FUNCTION: Insert Dimensions
# ============================================

def insert_dimensions(engine, df):
    """Insert or update dimension tables"""
    logger.info("Updating dimension tables")

    with engine.connect() as conn:

        # Countries
        all_countries = pd.concat([
            df['origin_country'].dropna(),
            df['destination_country'].dropna()
        ]).unique()

        country_query = text("""
            INSERT INTO dim_countries (country_code, country_name)
            VALUES (:code, :name)
            ON CONFLICT (country_code) DO NOTHING
        """)
        for code in all_countries:
            conn.execute(country_query, {"code": code, "name": code})
        conn.commit()
        logger.info(f"Processed {len(all_countries)} countries")

        # Transport modes
        result = conn.execute(text("SELECT COUNT(*) FROM dim_transport_modes"))
        mode_count = result.fetchone()[0]

        if mode_count == 0:
            mode_query = text("""
                INSERT INTO dim_transport_modes (mode_name, gco2_per_pkm, source)
                VALUES (:name, :gco2, :source)
            """)
            modes = [
                {'name': 'Night Train', 'gco2': 14, 'source': 'Back-on-Track 2022'},
                {'name': 'Day Train', 'gco2': 14, 'source': 'Back-on-Track 2022'},
                {'name': 'Airplane', 'gco2': 144, 'source': 'Back-on-Track 2022'},
            ]
            for mode in modes:
                conn.execute(mode_query, mode)
            conn.commit()
            logger.info(f"Added {len(modes)} transport modes")
        else:
            logger.info(f"Transport modes already populated ({mode_count} modes)")


# ============================================
# FUNCTION: Insert Facts
# ============================================

def insert_facts(engine, df):
    """Insert route data into fact_routes table"""
    logger.info(f"Loading {len(df)} routes into fact_routes")

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM fact_routes"))
        conn.commit()
        logger.info("Cleared existing fact_routes data")

    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()

        columns = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_sql = f"INSERT INTO fact_routes ({columns}) VALUES ({placeholders})"

        rows = [
            tuple(None if pd.isna(v) else v for v in row)
            for row in df.itertuples(index=False, name=None)
        ]

        chunk_size = 1000
        for i in range(0, len(rows), chunk_size):
            cursor.executemany(insert_sql, rows[i:i + chunk_size])
            logger.info(f"Inserted rows {i} to {min(i + chunk_size, len(rows))}")

        raw_conn.commit()
        cursor.close()
        logger.info(f"Successfully inserted {len(df)} routes")

    except Exception as e:
        raw_conn.rollback()
        logger.error(f"Insert failed: {str(e)}")
        raise e
    finally:
        raw_conn.close()


# ============================================
# FUNCTION: Validate Data
# ============================================

def validate_data(engine, original_count):
    """Validate loaded data against original CSV count"""
    logger.info("Validating loaded data")

    with engine.connect() as conn:

        # Row count
        result = conn.execute(text("SELECT COUNT(*) FROM fact_routes"))
        db_count = result.fetchone()[0]
        logger.info(f"CSV rows: {original_count} | Database rows: {db_count}")
        if db_count != original_count:
            logger.warning("Row count mismatch — some rows may have been filtered")

        # Null check
        result = conn.execute(text("""
            SELECT COUNT(*) FROM fact_routes
            WHERE origin IS NULL OR destination IS NULL OR distance_km IS NULL
        """))
        null_count = result.fetchone()[0]
        if null_count == 0:
            logger.info("No NULL values in critical columns")
        else:
            logger.warning(f"{null_count} rows have NULL critical values")

        # Summary statistics
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_routes,
                COUNT(DISTINCT origin_country) as countries,
                ROUND(AVG(distance_km)::numeric, 2) as avg_distance,
                ROUND(SUM(co2_savings_kg)::numeric, 2) as total_savings_kg,
                ROUND(AVG(savings_percent)::numeric, 2) as avg_savings_pct
            FROM fact_routes
        """))
        stats = result.fetchone()

        total_savings = stats[3] or 0
        logger.info(
            f"Summary — {stats[0]:,} routes | {stats[1]} countries | "
            f"avg distance: {stats[2]} km | "
            f"total CO2 saved: {total_savings:,.2f} kg ({total_savings/1000:,.2f} t) | "
            f"avg savings: {stats[4]}%"
        )

        # Top 5 routes
        result = conn.execute(text("""
            SELECT route_name_simple, origin_country, destination_country, co2_savings_kg
            FROM fact_routes
            WHERE co2_savings_kg IS NOT NULL
            ORDER BY co2_savings_kg DESC
            LIMIT 5
        """))
        for i, row in enumerate(result, 1):
            logger.info(f"Top {i}: {row[0]} — {row[3]:.2f} kg CO2 saved")


# ============================================
# MAIN
# ============================================

def main():
    logger.info("Starting database loading — ObRail Europe")

    # Resolve input CSV inside main() to avoid module-level side effects
    input_csv = PRIMARY_CSV
    if not os.path.exists(input_csv):
        logger.warning(f"{PRIMARY_CSV} not found — trying fallback")
        input_csv = FALLBACK_CSV

    engine = connect_database()
    if not engine:
        logger.error("Cannot proceed without database connection")
        return 1

    try:
        if not verify_schema(engine):
            logger.error("Schema verification failed")
            return 1

        df = load_csv_data(input_csv)
        if df is None:
            return 1

        original_count = len(df)
        df_clean = prepare_data(df)
        insert_dimensions(engine, df_clean)
        insert_facts(engine, df_clean)
        validate_data(engine, original_count)

        logger.info("Database loading complete")
        return 0

    except Exception as e:
        logger.error(f"Loading failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        engine.dispose()
        logger.info("Database connection closed")


if __name__ == "__main__":
    sys.exit(main())