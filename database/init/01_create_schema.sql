/* =========================================================
   OBRAIL EUROPE - DATABASE SCHEMA
   Schema for European Night Train Routes with Environmental Impact
   
   This schema stores individual routes with their CO2 calculations
   NOT aggregated data - each route is a separate record
   ========================================================= */

-- ========================================
-- DIMENSION TABLES
-- ========================================

-- Countries dimension
CREATE TABLE IF NOT EXISTS dim_countries (
    country_code VARCHAR(5) PRIMARY KEY,
    country_name VARCHAR(100)
);

-- Transport modes dimension  
CREATE TABLE IF NOT EXISTS dim_transport_modes (
    mode_id SERIAL PRIMARY KEY,
    mode_name VARCHAR(50) NOT NULL,
    gco2_per_pkm DECIMAL(10,2),
    source VARCHAR(100)
);

-- Train types dimension
CREATE TABLE IF NOT EXISTS dim_train_types (
    type_id SERIAL PRIMARY KEY,
    type_code VARCHAR(20) NOT NULL UNIQUE,
    type_name VARCHAR(50) NOT NULL
);

-- ========================================
-- FACT TABLE - ROUTES
-- ========================================

CREATE TABLE IF NOT EXISTS fact_routes (
    route_id SERIAL PRIMARY KEY,
    
    -- Route identification
    route_name VARCHAR(200),
    route_name_simple VARCHAR(200),
    
    -- Origin and destination
    origin VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    origin_country VARCHAR(5),
    destination_country VARCHAR(5),
    
    -- Route characteristics
    distance_km DECIMAL(10,2),
    service_type VARCHAR(20),
    train_type VARCHAR(20),
    
    -- Emission factors used
    train_gco2_pkm DECIMAL(10,2),
    plane_gco2_pkm DECIMAL(10,2),
    
    -- Calculated emissions (kg CO2)
    train_co2_kg DECIMAL(10,2),
    plane_co2_kg DECIMAL(10,2),
    co2_savings_kg DECIMAL(10,2),
    savings_percent DECIMAL(5,2),
    
    -- Metadata
    emission_source VARCHAR(100),
    calculation_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    CONSTRAINT fk_origin_country 
        FOREIGN KEY (origin_country) 
        REFERENCES dim_countries(country_code)
        ON DELETE SET NULL,
        
    CONSTRAINT fk_destination_country 
        FOREIGN KEY (destination_country) 
        REFERENCES dim_countries(country_code)
        ON DELETE SET NULL
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Search by country
CREATE INDEX IF NOT EXISTS idx_routes_origin_country 
    ON fact_routes(origin_country);

CREATE INDEX IF NOT EXISTS idx_routes_destination_country 
    ON fact_routes(destination_country);

-- Search by train type
CREATE INDEX IF NOT EXISTS idx_routes_train_type 
    ON fact_routes(train_type);

-- Search by service type
CREATE INDEX IF NOT EXISTS idx_routes_service_type 
    ON fact_routes(service_type);

-- Search by CO2 savings (for finding best routes)
CREATE INDEX IF NOT EXISTS idx_routes_co2_savings 
    ON fact_routes(co2_savings_kg DESC);

-- Search by distance
CREATE INDEX IF NOT EXISTS idx_routes_distance 
    ON fact_routes(distance_km);

-- ========================================
-- VIEWS FOR COMMON QUERIES
-- ========================================

-- Total CO2 savings by country
CREATE OR REPLACE VIEW v_savings_by_country AS
SELECT 
    origin_country,
    COUNT(*) as route_count,
    ROUND(SUM(co2_savings_kg), 2) as total_savings_kg,
    ROUND(AVG(co2_savings_kg), 2) as avg_savings_per_route_kg,
    ROUND(SUM(co2_savings_kg) / 1000, 2) as total_savings_tons
FROM fact_routes
WHERE origin_country IS NOT NULL
GROUP BY origin_country
ORDER BY total_savings_kg DESC;

-- Top routes by CO2 savings
CREATE OR REPLACE VIEW v_top_routes_savings AS
SELECT 
    route_name_simple,
    origin,
    destination,
    origin_country,
    destination_country,
    distance_km,
    train_type,
    co2_savings_kg,
    savings_percent
FROM fact_routes
WHERE co2_savings_kg IS NOT NULL
ORDER BY co2_savings_kg DESC
LIMIT 50;

-- Summary statistics
CREATE OR REPLACE VIEW v_summary_stats AS
SELECT 
    COUNT(*) as total_routes,
    COUNT(DISTINCT origin_country) as countries_covered,
    ROUND(AVG(distance_km), 2) as avg_distance_km,
    ROUND(SUM(co2_savings_kg), 2) as total_co2_saved_kg,
    ROUND(SUM(co2_savings_kg) / 1000, 2) as total_co2_saved_tons,
    ROUND(AVG(savings_percent), 2) as avg_savings_percent
FROM fact_routes;

-- Routes by train type
CREATE OR REPLACE VIEW v_routes_by_type AS
SELECT 
    train_type,
    COUNT(*) as route_count,
    ROUND(AVG(distance_km), 2) as avg_distance_km,
    ROUND(SUM(co2_savings_kg), 2) as total_savings_kg
FROM fact_routes
WHERE train_type IS NOT NULL
GROUP BY train_type
ORDER BY route_count DESC;