"""
Route Environmental Impact Calculator
======================================

Combines route data with CO2 emission factors to calculate 
environmental impact of train vs plane travel.

Inputs:
- all_routes_cleaned.csv (routes with countries and distances)
- co2_emissions_reference.csv (emission factors by transport mode)

Output:
- all_routes_environmental_impact.csv (routes with CO2 calculations)

Author: ObRail Europe Data Team
"""

import pandas as pd
import os

# ----------------------------
# CONFIGURATION
# ----------------------------
ROUTES_FILE = "data/transformed/all_routes_cleaned.csv"
CO2_REFERENCE_FILE = "data/transformed/emissions_reference.csv"
OUTPUT_FILE = "data/transformed/environmental_impact.csv"

# Default emission factors (g CO2 per passenger-km)
# Used if reference file cannot be read
DEFAULT_EMISSION_FACTORS = {
    'train': 14,
    'plane': 144,
    'car': 132
}

# ----------------------------
# FUNCTION: Load emission factors
# ----------------------------
def load_emission_factors(file_path):
    """
    Load CO2 emission factors from reference file
    
    Returns: dict with emission factors for each transport mode
    """
    
    print("\n📊 Loading CO2 Emission Factors")
    print("─" * 70)
    
    try:
        df = pd.read_csv(file_path)
        
        # Extract emission factors
        factors = {}
        
        # Find train emissions
        train_row = df[df['transport_mode'].str.contains('Night Train', case=False, na=False)]
        if not train_row.empty:
            factors['train'] = train_row['gco2_per_pkm'].values[0]
        
        # Find plane emissions (without SAF - standard aviation fuel)
        plane_row = df[df['transport_mode'] == 'Plane']
        if not plane_row.empty:
            factors['plane'] = plane_row['gco2_per_pkm'].values[0]
        
        # Find car emissions
        car_row = df[df['transport_mode'].str.contains('Car', case=False, na=False)]
        if not car_row.empty:
            factors['car'] = car_row['gco2_per_pkm'].values[0]
        
        print(f"✓ Loaded emission factors from {file_path}")
        print(f"  Train: {factors.get('train', 'N/A')} g CO2/pkm")
        print(f"  Plane: {factors.get('plane', 'N/A')} g CO2/pkm")
        print(f"  Car: {factors.get('car', 'N/A')} g CO2/pkm")
        
        return factors
        
    except Exception as e:
        print(f"⚠️  Could not load {file_path}: {e}")
        print(f"⚠️  Using default emission factors")
        print(f"  Train: {DEFAULT_EMISSION_FACTORS['train']} g CO2/pkm")
        print(f"  Plane: {DEFAULT_EMISSION_FACTORS['plane']} g CO2/pkm")
        print(f"  Car: {DEFAULT_EMISSION_FACTORS['car']} g CO2/pkm")
        return DEFAULT_EMISSION_FACTORS

# ----------------------------
# FUNCTION: Calculate route emissions
# ----------------------------
def calculate_route_emissions(routes_df, emission_factors):
    """
    Calculate CO2 emissions for each route
    
    Args:
        routes_df: DataFrame with route data
        emission_factors: dict with emission factors per transport mode
    
    Returns: DataFrame with added CO2 columns
    """
    
    print("\n🧮 Calculating Environmental Impact")
    print("─" * 70)
    
    # Make a copy to avoid modifying original
    df = routes_df.copy()
    
    # Get emission factors
    train_factor = emission_factors.get('train', DEFAULT_EMISSION_FACTORS['train'])
    plane_factor = emission_factors.get('plane', DEFAULT_EMISSION_FACTORS['plane'])
    
    # Add emission factor columns (for reference)
    df['train_gco2_pkm'] = train_factor
    df['plane_gco2_pkm'] = plane_factor
    
    # Calculate total CO2 emissions per route (in kg)
    # Formula: distance (km) × emission factor (g/pkm) ÷ 1000 = kg CO2
    df['train_co2_kg'] = (df['distance_km'] * train_factor) / 1000
    df['plane_co2_kg'] = (df['distance_km'] * plane_factor) / 1000
    
    # Calculate CO2 savings (plane - train)
    df['co2_savings_kg'] = df['plane_co2_kg'] - df['train_co2_kg']
    
    # Calculate savings as percentage
    df['savings_percent'] = (df['co2_savings_kg'] / df['plane_co2_kg']) * 100
    
    # Round for readability
    df['train_co2_kg'] = df['train_co2_kg'].round(2)
    df['plane_co2_kg'] = df['plane_co2_kg'].round(2)
    df['co2_savings_kg'] = df['co2_savings_kg'].round(2)
    df['savings_percent'] = df['savings_percent'].round(1)
    
    # Add metadata
    df['emission_source'] = 'Back-on-Track 2019'
    df['calculation_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    print(f"✓ Calculated emissions for {len(df)} routes")
    
    return df

# ----------------------------
# FUNCTION: Generate summary statistics
# ----------------------------
def generate_summary_statistics(df):
    """
    Generate summary statistics about environmental impact
    """
    
    print("\n📈 Environmental Impact Summary")
    print("─" * 70)
    
    # Overall statistics
    total_routes = len(df)
    total_train_co2 = df['train_co2_kg'].sum()
    total_plane_co2 = df['plane_co2_kg'].sum()
    total_savings = df['co2_savings_kg'].sum()
    
    print(f"\n🌍 Overall Impact:")
    print(f"   Total routes analyzed: {total_routes}")
    print(f"   Total train CO2: {total_train_co2:,.2f} kg")
    print(f"   Total plane CO2: {total_plane_co2:,.2f} kg")
    print(f"   Total CO2 savings: {total_savings:,.2f} kg ({total_savings/1000:,.2f} tons)")
    print(f"   Average savings per route: {total_savings/total_routes:,.2f} kg")
    
    # Top 10 routes by CO2 savings
    print(f"\n🏆 Top 10 Routes by CO2 Savings:")
    top_routes = df.nlargest(10, 'co2_savings_kg')[
        ['origin', 'destination', 'origin_country', 'destination_country', 
         'distance_km', 'co2_savings_kg']
    ]
    print(top_routes.to_string(index=False))
    
    # Breakdown by origin country
    print(f"\n🌐 CO2 Savings by Origin Country:")
    country_summary = df.groupby('origin_country').agg({
        'co2_savings_kg': 'sum',
        'origin': 'count'
    }).rename(columns={'origin': 'route_count'}).sort_values('co2_savings_kg', ascending=False)
    
    country_summary['co2_savings_tons'] = (country_summary['co2_savings_kg'] / 1000).round(2)
    print(country_summary[['route_count', 'co2_savings_tons']].head(10).to_string())
    
    # Breakdown by route type
    if 'type' in df.columns:
        print(f"\n🌙 CO2 Savings by Train Type:")
        type_summary = df.groupby('type').agg({
            'co2_savings_kg': 'sum',
            'origin': 'count'
        }).rename(columns={'origin': 'route_count'})
        type_summary['co2_savings_tons'] = (type_summary['co2_savings_kg'] / 1000).round(2)
        print(type_summary[['route_count', 'co2_savings_tons']].to_string())

# ----------------------------
# MAIN FUNCTION
# ----------------------------
def main():
    """
    Main execution function
    """
    
    print("\n" + "=" * 70)
    print("🌍 ROUTE ENVIRONMENTAL IMPACT CALCULATOR")
    print("=" * 70)
    
    # Check if input files exist
    if not os.path.exists(ROUTES_FILE):
        print(f"\n❌ ERROR: Routes file not found: {ROUTES_FILE}")
        print(f"   Please run the extraction and transformation scripts first.")
        return
    
    if not os.path.exists(CO2_REFERENCE_FILE):
        print(f"\n⚠️  WARNING: CO2 reference file not found: {CO2_REFERENCE_FILE}")
        print(f"   Will use default emission factors.")
    
    try:
        # 1. Load emission factors
        emission_factors = load_emission_factors(CO2_REFERENCE_FILE)
        
        # 2. Load routes data
        print(f"\n📂 Loading Routes Data")
        print("─" * 70)
        routes_df = pd.read_csv(ROUTES_FILE)
        print(f"✓ Loaded {len(routes_df)} routes from {ROUTES_FILE}")
        
        # Check if distance column exists
        if 'distance_km' not in routes_df.columns:
            print(f"\n❌ ERROR: 'distance_km' column not found in routes file")
            print(f"   Available columns: {list(routes_df.columns)}")
            print(f"   Cannot calculate CO2 without distance data.")
            return
        
        # 3. Calculate emissions
        routes_with_co2 = calculate_route_emissions(routes_df, emission_factors)
        
        # 4. Save results
        print(f"\n💾 Saving Results")
        print("─" * 70)
        
        # Create output directory if needed
        output_dir = os.path.dirname(OUTPUT_FILE)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        routes_with_co2.to_csv(OUTPUT_FILE, index=False)
        print(f"✓ Saved: {OUTPUT_FILE}")
        
        # 5. Generate summary statistics
        generate_summary_statistics(routes_with_co2)
        
        # 6. Display sample of results
        print(f"\n📋 Sample Results (first 5 routes):")
        print("─" * 70)
        sample_cols = ['origin', 'destination', 'origin_country', 'destination_country', 
                    'distance_km', 'train_co2_kg', 'plane_co2_kg', 'co2_savings_kg', 'savings_percent']
        available_cols = [col for col in sample_cols if col in routes_with_co2.columns]
        print(routes_with_co2[available_cols].head().to_string(index=False))
        
        print("\n" + "=" * 70)
        print("✅ CALCULATION COMPLETE")
        print("=" * 70)
        
        print(f"\n📊 Next Steps:")
        print(f"   1. Review results in: {OUTPUT_FILE}")
        print(f"   2. Use this data for environmental impact analysis")
        print(f"   3. Create visualizations showing CO2 savings")
        print(f"   4. Support policy recommendations with data")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()