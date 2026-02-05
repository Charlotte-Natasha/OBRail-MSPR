"""
Comprehensive Back-on-Track Data Extraction
============================================

Extracts multiple datasets from the Back-on-Track ODS file:
1. CO2 emissions by transport mode
2. Flight routes replaceable by trains
3. Country-level emissions data

Author: ObRail Europe Data Team
"""

import pandas as pd
import os

# ----------------------------
# CONFIGURATION
# ----------------------------
INPUT_FILE = "data/raw/co2/Emissions.ods"
OUTPUT_DIR = "data/transformed/"

# ----------------------------
# FUNCTION 1: Extract CO2 emissions by mode
# ----------------------------
def extract_emissions_by_mode(file_path):
    """Extract CO2 emissions per transport mode"""
    
    print("\n📊 Extracting: CO2 Emissions by Transport Mode")
    print("─" * 70)
    
    # Read GHGbyMeans sheet
    df = pd.read_excel(file_path, sheet_name='GHGbyMeans', engine='odf')
    
    # Extract first 3 columns (transport mode, basic CO2, CO2 with RF)
    df_clean = df.iloc[:, 0:3].copy()
    df_clean.columns = ['transport_mode', 'gco2_per_pkm', 'gco2_per_pkm_rf3']
    
    # Clean data
    df_clean = df_clean.dropna(subset=['transport_mode'])  # Remove rows with no transport mode
    df_clean['transport_mode'] = df_clean['transport_mode'].str.replace('*', '', regex=False).str.strip()
    
    # Convert to numeric
    df_clean['gco2_per_pkm'] = pd.to_numeric(df_clean['gco2_per_pkm'], errors='coerce')
    df_clean['gco2_per_pkm_rf3'] = pd.to_numeric(df_clean['gco2_per_pkm_rf3'], errors='coerce')
    
    # Add metadata
    df_clean['source'] = 'Back-on-Track'
    df_clean['year'] = 2019
    
    print(f"✓ Extracted {len(df_clean)} transport modes")
    print(df_clean.to_string(index=False))
    
    return df_clean

# ----------------------------
# FUNCTION 2: Extract flight routes (sample)
# ----------------------------
def extract_flight_routes(file_path, sample_size=100):
    """Extract sample of flight routes replaceable by trains"""
    
    print("\n✈️  Extracting: Flight Routes (Sample)")
    print("─" * 70)
    
    # Read Flights2019 sheet
    df = pd.read_excel(file_path, sheet_name='Flights2019', engine='odf', skiprows=3)
    
    # The data starts after header rows
    # Key columns: 1stCity, 2ndCity, PAX (passengers), Distance, TrainTime
    
    # Try to identify the column names
    # Based on what we saw, columns are around positions 12-16
    try:
        # Select relevant columns (adjust based on actual structure)
        df_clean = df[['1stCity', '2ndCity', 'PAX', 'Distance', 'TrainTime', 
                      'AviationEmissions', 'NightTrain']].copy()
        
        # Clean column names
        df_clean.columns = ['origin_city', 'destination_city', 'passengers_2019', 
                           'distance_km', 'train_time_hours', 'aviation_emissions_tco2e', 
                           'train_emissions_tco2e']
        
        # Remove rows with missing critical data
        df_clean = df_clean.dropna(subset=['origin_city', 'destination_city'])
        
        # Convert numeric columns
        numeric_cols = ['passengers_2019', 'distance_km', 'train_time_hours', 
                       'aviation_emissions_tco2e', 'train_emissions_tco2e']
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        # Calculate CO2 savings
        if 'aviation_emissions_tco2e' in df_clean.columns and 'train_emissions_tco2e' in df_clean.columns:
            df_clean['co2_savings_tco2e'] = df_clean['aviation_emissions_tco2e'] - df_clean['train_emissions_tco2e']
        
        # Take sample
        df_sample = df_clean.head(sample_size)
        
        print(f"✓ Extracted {len(df_sample)} flight routes (sample)")
        print(f"\nTop 5 routes by CO2 savings potential:")
        if 'co2_savings_tco2e' in df_sample.columns:
            top_routes = df_sample.nlargest(5, 'co2_savings_tco2e')[
                ['origin_city', 'destination_city', 'passengers_2019', 'co2_savings_tco2e']
            ]
            print(top_routes.to_string(index=False))
        
        return df_sample
        
    except Exception as e:
        print(f"⚠️  Could not extract flight routes: {str(e)}")
        print("   This is optional data - continuing with emissions data only")
        return pd.DataFrame()

# ----------------------------
# FUNCTION 3: Create summary statistics
# ----------------------------
def create_summary_statistics(emissions_df):
    """Create summary statistics for presentation"""
    
    print("\n📈 Creating Summary Statistics")
    print("─" * 70)
    
    summary = {
        'transport_mode': [],
        'gco2_per_pkm': [],
        'vs_plane_savings_percent': [],
        'vs_car_savings_percent': []
    }
    
    # Get plane emissions as baseline
    plane_emissions = emissions_df[
        emissions_df['transport_mode'].str.contains('Plane', na=False)
    ]['gco2_per_pkm'].values
    
    car_emissions = emissions_df[
        emissions_df['transport_mode'].str.contains('Car', na=False)
    ]['gco2_per_pkm'].values
    
    if len(plane_emissions) > 0:
        plane_baseline = plane_emissions[0]
    else:
        plane_baseline = None
    
    if len(car_emissions) > 0:
        car_baseline = car_emissions[0]
    else:
        car_baseline = None
    
    # Calculate savings for each mode
    for _, row in emissions_df.iterrows():
        mode = row['transport_mode']
        emissions = row['gco2_per_pkm']
        
        if pd.notna(emissions):
            summary['transport_mode'].append(mode)
            summary['gco2_per_pkm'].append(emissions)
            
            # vs Plane
            if plane_baseline:
                savings = ((plane_baseline - emissions) / plane_baseline) * 100
                summary['vs_plane_savings_percent'].append(round(savings, 1))
            else:
                summary['vs_plane_savings_percent'].append(None)
            
            # vs Car
            if car_baseline:
                savings = ((car_baseline - emissions) / car_baseline) * 100
                summary['vs_car_savings_percent'].append(round(savings, 1))
            else:
                summary['vs_car_savings_percent'].append(None)
    
    summary_df = pd.DataFrame(summary)
    
    print("✓ Summary statistics:")
    print(summary_df.to_string(index=False))
    
    return summary_df

# ----------------------------
# MAIN FUNCTION
# ----------------------------
def main():
    """Main execution function"""
    
    print("\n" + "=" * 70)
    print("🧹 BACK-ON-TRACK DATA EXTRACTION & CLEANING")
    print("=" * 70)
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"\n❌ ERROR: Input file not found: {INPUT_FILE}")
        print(f"\n📝 What to do:")
        print(f"   1. Create folder: {os.path.dirname(INPUT_FILE)}")
        print(f"   2. Place the ODS file there")
        print(f"   3. Run this script again")
        return
    
    print(f"✓ Found input file: {INPUT_FILE}")
    
    # Create output directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"✓ Created output directory: {OUTPUT_DIR}")
    
    try:
        # 1. Extract emissions by mode (PRIORITY)
        emissions_df = extract_emissions_by_mode(INPUT_FILE)
        
        # Save emissions data
        emissions_file = os.path.join(OUTPUT_DIR, "emissions_reference.csv")
        emissions_df.to_csv(emissions_file, index=False)
        print(f"\n💾 Saved: {emissions_file}")
        
        # 2. Create summary statistics
        summary_df = create_summary_statistics(emissions_df)
        
        # Save summary
        summary_file = os.path.join(OUTPUT_DIR, "emissions_summary.csv")
        summary_df.to_csv(summary_file, index=False)
        print(f"💾 Saved: {summary_file}")
        
        # 3. Extract flight routes (optional - may fail, that's OK)
        print("\n" + "=" * 70)
        print("Optional: Extracting flight routes data...")
        print("=" * 70)
        
        try:
            routes_df = extract_flight_routes(INPUT_FILE, sample_size=50)
            if not routes_df.empty:
                routes_file = os.path.join(OUTPUT_DIR, "replaceable_flight_routes_sample.csv")
                routes_df.to_csv(routes_file, index=False)
                print(f"💾 Saved: {routes_file}")
        except Exception as e:
            print(f"⚠️  Skipping flight routes extraction: {str(e)}")
        
        # Final summary
        print("\n" + "=" * 70)
        print("✅ EXTRACTION COMPLETE")
        print("=" * 70)
        
        print(f"\n📁 Output files created:")
        print(f"   1. {emissions_file}")
        print(f"   2. {summary_file}")
        
        print(f"\n💡 KEY FINDINGS:")
        
        # Find train and plane emissions
        train_row = emissions_df[emissions_df['transport_mode'].str.contains('Night Train', na=False)]
        plane_row = emissions_df[emissions_df['transport_mode'].str.contains('Plane', na=False, regex=False)]
        
        if not train_row.empty and not plane_row.empty:
            train_em = train_row['gco2_per_pkm'].values[0]
            plane_em = plane_row['gco2_per_pkm'].values[0]
            savings = ((plane_em - train_em) / plane_em) * 100
            
            print(f"   🚂 Night Train: {train_em} g CO2/pkm")
            print(f"   ✈️  Airplane: {plane_em} g CO2/pkm")
            print(f"   🌍 Savings: {savings:.1f}% less CO2 with night trains!")
        
        print(f"\n📊 Use these files in your project to:")
        print(f"   - Show environmental benefits of rail")
        print(f"   - Compare transport mode emissions")
        print(f"   - Calculate CO2 savings per route")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()