"""
ObRail Europe - Database Loading Script
========================================

Loads transformed route data with environmental impact into PostgreSQL.

This script:
1. Connects to PostgreSQL using SQLAlchemy (modern Python standard)
2. Verifies the database schema was created correctly
3. Loads CSV data from the transformation phase
4. Inserts data into dimension and fact tables
5. Validates the loaded data

Uses SQLAlchemy for:
- Cleaner, more maintainable code
- Automatic connection management
- Easy pandas integration with .to_sql()

Author: ObRail Europe Data Team
Version: 2.0 - Corrected Schema
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================

# Load environment variables from .env file
# This file contains database credentials (never commit to git!)
load_dotenv()

# Input CSV file from the transformation phase
# This contains all routes with CO2 calculations
INPUT_CSV = "data/transformed/environmental_impact.csv"

# Fallback to alternative filename if needed
if not os.path.exists(INPUT_CSV):
    INPUT_CSV = "data/transformed/all_routes_environmental_impact.csv"

# Build database connection URL from environment variables
# Format: postgresql://username:password@host:port/database
DATABASE_URL = os.getenv(
    'DATABASE_URL',  # Try this first (full URL)
    # If not set, build from individual components
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
    """
    Connect to PostgreSQL database using SQLAlchemy.
    
    Returns:
        engine: SQLAlchemy engine object, or None if connection failed
    
    Why SQLAlchemy?
    - Cleaner syntax than raw psycopg2
    - Automatic connection pooling
    - Better error handling
    - Works seamlessly with pandas
    """
    
    print("\n📡 Connecting to PostgreSQL database...")
    
    # Hide password in printed URL for security
    safe_url = DATABASE_URL.replace(
        os.getenv('POSTGRES_PASSWORD', ''), 
        '****'
    )
    print(f"   Using: {safe_url}")
    
    try:
        # Create SQLAlchemy engine
        # This manages database connections for us
        engine = create_engine(DATABASE_URL)
        
        # Test the connection with a simple query
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print("   ✓ Connection successful!")
        return engine
        
    except Exception as e:
        print(f"   ✗ Connection failed: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("   1. Is PostgreSQL running? Check: docker ps")
        print("   2. Start Docker: docker-compose up -d")
        print("   3. Verify .env file has correct credentials")
        print(f"   4. Check port {os.getenv('POSTGRES_PORT', '5433')} is correct")
        return None

# ============================================
# FUNCTION: Verify Database Schema
# ============================================

def verify_schema(engine):
    """
    Verify that database tables were created correctly.
    
    Checks for:
    - dim_countries (dimension table for countries)
    - dim_transport_modes (dimension table for transport types)
    - dim_train_types (dimension table for train types)
    - fact_routes (fact table for route data)
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        bool: True if schema is correct, False otherwise
    """
    
    print("\n🔍 Verifying database schema...")
    
    # Query to get all table names in the public schema
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        
        # Extract table names from query results
        tables = [row[0] for row in result]
        print(f"   Found {len(tables)} tables: {', '.join(tables)}")
        
        # Required tables for our application
        # These must exist for the loading to work
        required_tables = [
            'dim_countries',      # Countries reference data
            'dim_transport_modes', # Transport modes reference data
            'fact_routes'         # Main route data
        ]
        
        # Check if any required tables are missing
        missing = [t for t in required_tables if t not in tables]
        
        if missing:
            print(f"   ✗ Missing tables: {', '.join(missing)}")
            print("\n💡 Fix:")
            print("   Schema not initialized. Reset Docker:")
            print("   docker-compose down -v")
            print("   docker-compose up -d")
            return False
        
        print("   ✓ All required tables exist!")
        return True

# ============================================
# FUNCTION: Load CSV Data
# ============================================

def load_csv_data():
    """
    Load the transformed CSV file with route and environmental data.
    
    The CSV should contain columns like:
    - origin, destination (city names)
    - origin_country, destination_country (country codes)
    - distance_km (route distance)
    - train_co2_kg, plane_co2_kg (emissions in kg)
    - co2_savings_kg, savings_percent (calculated savings)
    
    Returns:
        DataFrame: Pandas DataFrame with route data, or None if failed
    """
    
    print(f"\n📂 Loading CSV data...")
    print(f"   File: {INPUT_CSV}")
    
    # Check if file exists
    if not os.path.exists(INPUT_CSV):
        print(f"   ✗ File not found!")
        print("   Make sure you ran the transformation phase first:")
        print("   python scripts/calculate_co2.py")
        return None
    
    try:
        # Load CSV into pandas DataFrame
        df = pd.read_csv(INPUT_CSV)
        
        print(f"   ✓ Loaded {len(df)} rows")
        print(f"   Columns: {len(df.columns)} ({', '.join(list(df.columns)[:5])}...)")
        
        return df
        
    except Exception as e:
        print(f"   ✗ Error reading CSV: {str(e)}")
        return None

# ============================================
# FUNCTION: Prepare Data for Database
# ============================================

def prepare_data(df):
    """
    Prepare and clean DataFrame for database insertion.
    
    This function:
    - Maps CSV columns to database columns
    - Handles missing values
    - Converts data types
    - Removes invalid rows
    
    Args:
        df: Raw DataFrame from CSV
    
    Returns:
        DataFrame: Cleaned DataFrame ready for insertion
    """
    
    print("\n🔄 Preparing data for database...")
    
    # Create new DataFrame with database column names
    # Map CSV columns to database schema
    df_clean = pd.DataFrame()
    
    # Route identification
    df_clean['route_name'] = df.get('route_name', df.get('route_name_simple'))
    df_clean['route_name_simple'] = df.get('route_name_simple', df.get('route_name'))
    
    # Origin and destination (REQUIRED)
    df_clean['origin'] = df['origin']
    df_clean['destination'] = df['destination']
    
    # Countries (REQUIRED - foreign keys to dim_countries)
    df_clean['origin_country'] = df['origin_country']
    df_clean['destination_country'] = df['destination_country']
    
    # Route characteristics
    df_clean['distance_km'] = df['distance_km']
    
    # Service type and train type
    # Handle both possible column names
    df_clean['service_type'] = df.get('service_type', df.get('type'))
    df_clean['train_type'] = df.get('type', df.get('service_type'))
    
    # Emission factors used in calculation
    df_clean['train_gco2_pkm'] = df.get('train_gco2_pkm', 14)  # Default: 14 g/pkm
    df_clean['plane_gco2_pkm'] = df.get('plane_gco2_pkm', 144)  # Default: 144 g/pkm
    
    # Calculated emissions (kg CO2)
    df_clean['train_co2_kg'] = df['train_co2_kg']
    df_clean['plane_co2_kg'] = df['plane_co2_kg']
    df_clean['co2_savings_kg'] = df['co2_savings_kg']
    df_clean['savings_percent'] = df['savings_percent']
    
    # Metadata
    df_clean['emission_source'] = df.get('emission_source', 'Back-on-Track 2022')
    
    # Convert calculation_date to proper date format
    # Use existing date or today's date
    df_clean['calculation_date'] = pd.to_datetime(
        df.get('calculation_date', datetime.now().date())
    )
    
    # Data quality: Remove rows with NULL in critical columns
    # These columns MUST have values for the route to be valid
    before_count = len(df_clean)
    df_clean = df_clean.dropna(subset=[
        'origin',
        'destination', 
        'distance_km'
    ])
    after_count = len(df_clean)
    
    # Report if any rows were removed
    if before_count != after_count:
        removed = before_count - after_count
        print(f"   ⚠️  Removed {removed} rows with NULL critical values")
    
    print(f"   ✓ Prepared {len(df_clean)} valid rows")
    
    return df_clean

# ============================================
# FUNCTION: Insert Dimension Data
# ============================================

def insert_dimensions(engine, df):
    """
    Insert or update dimension tables (reference data).
    
    Dimension tables contain:
    - Countries (country codes and names)
    - Transport modes (with emission factors)
    
    These are relatively static reference data.
    
    Args:
        engine: SQLAlchemy engine
        df: DataFrame with route data
    """
    
    print("\n📊 Updating dimension tables...")
    
    with engine.connect() as conn:
        
        # ----------------------------------------
        # 1. INSERT COUNTRIES
        # ----------------------------------------
        
        print("   → Processing countries...")
        
        # Extract unique countries from both origin and destination
        # Use pd.concat to combine both columns
        all_countries = pd.concat([
            df['origin_country'].dropna(),
            df['destination_country'].dropna()
        ]).unique()
        
        # Insert each country (skip if already exists)
        # ON CONFLICT DO NOTHING = don't error if country already in table
        country_query = text("""
            INSERT INTO dim_countries (country_code, country_name)
            VALUES (:code, :name)
            ON CONFLICT (country_code) DO NOTHING
        """)
        
        # Insert each country
        # For now, use country_code as country_name (can enhance later)
        for code in all_countries:
            conn.execute(country_query, {"code": code, "name": code})
        
        conn.commit()
        print(f"      Processed {len(all_countries)} countries")
        
        # ----------------------------------------
        # 2. CHECK TRANSPORT MODES
        # ----------------------------------------
        
        print("   → Checking transport modes...")
        
        # Check if transport modes already populated
        result = conn.execute(text("SELECT COUNT(*) FROM dim_transport_modes"))
        mode_count = result.fetchone()[0]
        
        if mode_count == 0:
            # No transport modes yet, insert them
            print("      Adding transport modes...")
            
            mode_query = text("""
                INSERT INTO dim_transport_modes (mode_name, gco2_per_pkm, source)
                VALUES (:name, :gco2, :source)
            """)
            
            # Transport modes from Back-on-Track data
            modes = [
                {'name': 'Night Train', 'gco2': 14, 'source': 'Back-on-Track 2022'},
                {'name': 'Day Train', 'gco2': 14, 'source': 'Back-on-Track 2022'},
                {'name': 'Airplane', 'gco2': 144, 'source': 'Back-on-Track 2022'},
            ]
            
            for mode in modes:
                conn.execute(mode_query, mode)
            
            conn.commit()
            print(f"      Added {len(modes)} transport modes")
        else:
            print(f"      ✓ Already populated ({mode_count} modes)")

# ============================================
# FUNCTION: Insert Fact Data
# ============================================

def insert_facts(engine, df):
    print("\n💾 Loading data into fact_routes table...")

    with engine.connect() as conn:
        print("   Clearing existing routes...")
        conn.execute(text("DELETE FROM fact_routes"))
        conn.commit()

    print(f"   Inserting {len(df)} routes...")

    # Use psycopg2 directly to avoid pandas version compatibility issues
    from sqlalchemy import inspect
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()

        columns = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_sql = f"INSERT INTO fact_routes ({columns}) VALUES ({placeholders})"

        # Convert DataFrame to list of tuples, replacing NaN with None
        rows = [
            tuple(None if pd.isna(v) else v for v in row)
            for row in df.itertuples(index=False, name=None)
        ]

        # Insert in chunks of 1000
        chunk_size = 1000
        for i in range(0, len(rows), chunk_size):
            cursor.executemany(insert_sql, rows[i:i + chunk_size])

        raw_conn.commit()
        cursor.close()
        print(f"   ✓ Successfully inserted {len(df)} routes!")

    except Exception as e:
        raw_conn.rollback()
        raise e
    finally:
        raw_conn.close()        

# ============================================
# FUNCTION: Validate Loaded Data
# ============================================

def validate_data(engine, original_count):
    """
    Validate that data was loaded correctly.
    
    Checks:
    - Row count matches
    - No unexpected NULL values
    - Summary statistics make sense
    
    Args:
        engine: SQLAlchemy engine
        original_count: Number of rows in CSV
    """
    
    print("\n✅ Validating loaded data...")
    
    with engine.connect() as conn:
        
        # ----------------------------------------
        # 1. CHECK ROW COUNT
        # ----------------------------------------
        
        result = conn.execute(text("SELECT COUNT(*) FROM fact_routes"))
        db_count = result.fetchone()[0]
        
        print(f"\n   Row Count Validation:")
        print(f"   CSV rows: {original_count}")
        print(f"   Database rows: {db_count}")
        
        if db_count == original_count:
            print("   ✓ Counts match!")
        else:
            print("   ⚠️  Count mismatch - some rows may have been filtered")
        
        # ----------------------------------------
        # 2. CHECK FOR NULLS
        # ----------------------------------------
        
        print(f"\n   Data Quality Check:")
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM fact_routes
            WHERE origin IS NULL 
               OR destination IS NULL
               OR distance_km IS NULL
        """))
        
        null_count = result.fetchone()[0]
        
        if null_count == 0:
            print("   ✓ No NULL values in critical columns")
        else:
            print(f"   ⚠️  {null_count} rows have NULL critical values")
        
        # ----------------------------------------
        # 3. SUMMARY STATISTICS
        # ----------------------------------------
        
        print(f"\n   📊 Summary Statistics:")
        
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
        
        print(f"   Total routes: {stats[0]:,}")
        print(f"   Countries covered: {stats[1]}")
        print(f"   Average distance: {stats[2]} km")
        print(f"   Total CO2 saved: {stats[3]:,.2f} kg ({stats[3]/1000:,.2f} tons)")
        print(f"   Average savings: {stats[4]}%")
        
        # ----------------------------------------
        # 4. TOP ROUTES BY SAVINGS
        # ----------------------------------------
        
        print(f"\n   🏆 Top 5 Routes by CO2 Savings:")
        
        result = conn.execute(text("""
            SELECT 
                route_name_simple,
                origin_country,
                destination_country,
                distance_km,
                co2_savings_kg
            FROM fact_routes
            WHERE co2_savings_kg IS NOT NULL
            ORDER BY co2_savings_kg DESC
            LIMIT 5
        """))
        
        for i, row in enumerate(result, 1):
            print(f"   {i}. {row[0]}: {row[4]:.2f} kg CO2 saved")

# ============================================
# MAIN FUNCTION
# ============================================

def main():
    """
    Main execution function.
    
    Orchestrates the complete loading process:
    1. Connect to database
    2. Verify schema exists
    3. Load CSV data
    4. Prepare data for insertion
    5. Insert dimensions (countries, modes)
    6. Insert facts (routes)
    7. Validate everything loaded correctly
    
    Returns:
        int: 0 if successful, 1 if failed
    """
    
    # Print header
    print("\n" + "=" * 70)
    print("🗄️  DATABASE LOADING - ObRail Europe")
    print("=" * 70)
    print("\nLoading route data with environmental impact calculations")
    print("into PostgreSQL database...")
    
    # ----------------------------------------
    # STEP 1: CONNECT
    # ----------------------------------------
    
    engine = connect_database()
    if not engine:
        print("\n❌ Cannot proceed without database connection")
        return 1
    
    try:
        # ----------------------------------------
        # STEP 2: VERIFY SCHEMA
        # ----------------------------------------
        
        if not verify_schema(engine):
            print("\n❌ Schema verification failed")
            print("Make sure database was initialized correctly")
            return 1
        
        # ----------------------------------------
        # STEP 3: LOAD CSV
        # ----------------------------------------
        
        df = load_csv_data()
        if df is None:
            print("\n❌ Cannot load CSV data")
            return 1
        
        original_count = len(df)
        
        # ----------------------------------------
        # STEP 4: PREPARE DATA
        # ----------------------------------------
        
        df_clean = prepare_data(df)
        
        # ----------------------------------------
        # STEP 5: INSERT DIMENSIONS
        # ----------------------------------------
        
        insert_dimensions(engine, df_clean)
        
        # ----------------------------------------
        # STEP 6: INSERT FACTS
        # ----------------------------------------
        
        insert_facts(engine, df_clean)
        
        # ----------------------------------------
        # STEP 7: VALIDATE
        # ----------------------------------------
        
        validate_data(engine, original_count)
        
        # ----------------------------------------
        # SUCCESS!
        # ----------------------------------------
        
        print("\n" + "=" * 70)
        print("✅ DATABASE LOADING COMPLETE!")
        print("=" * 70)
        
        print("\n💡 Next Steps:")
        print("   1. Test queries:")
        print("      docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db")
        print("      SELECT * FROM v_summary_stats;")
        print("   2. View top routes:")
        print("      SELECT * FROM v_top_routes_savings LIMIT 10;")
        print("   3. Build REST API to serve this data")
        print("   4. Create dashboard for visualization")
        
        return 0
        
    except Exception as e:
        # Handle any unexpected errors
        print(f"\n❌ Error during loading: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Always close database connection
        engine.dispose()
        print("\n🔌 Database connection closed")

# ============================================
# SCRIPT ENTRY POINT
# ============================================

if __name__ == "__main__":
    # Run main function and exit with its return code
    # 0 = success, 1 = failure
    success = main()
    sys.exit(success)