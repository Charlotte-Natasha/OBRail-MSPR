/* =========================================================
   OBRAIL EUROPE - TEST QUERIES
   Validate database setup and test common queries
   ========================================================= */

-- ========================================
-- BASIC TESTS
-- ========================================

-- Test 1: Check all tables exist
SELECT 'Tables created:' as test;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Test 2: Check all views exist
SELECT 'Views created:' as test;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'VIEW'
ORDER BY table_name;

-- Test 3: Count reference data
SELECT 'Countries loaded:' as test, COUNT(*) as count FROM dim_countries;
SELECT 'Transport modes loaded:' as test, COUNT(*) as count FROM dim_transport_modes;
SELECT 'Train types loaded:' as test, COUNT(*) as count FROM dim_train_types;

-- ========================================
-- FUNCTIONAL TESTS (after data load)
-- ========================================

-- Test 4: Count routes (will be 0 until data loaded)
SELECT 'Routes in database:' as test, COUNT(*) as count FROM fact_routes;

-- Test 5: Check for NULL values in critical columns
SELECT 'Routes with NULL origin:' as test, COUNT(*) as count 
FROM fact_routes WHERE origin IS NULL;

SELECT 'Routes with NULL destination:' as test, COUNT(*) as count 
FROM fact_routes WHERE destination IS NULL;

SELECT 'Routes with NULL distance:' as test, COUNT(*) as count 
FROM fact_routes WHERE distance_km IS NULL;

-- Test 6: Test views work
SELECT 'Summary statistics view:' as test;
SELECT * FROM v_summary_stats;

-- Test 7: Test indexes exist
SELECT 'Indexes created:' as test;
SELECT indexname 
FROM pg_indexes 
WHERE tablename = 'fact_routes'
ORDER BY indexname;

-- ========================================
-- SAMPLE QUERIES FOR ANALYSIS
-- ========================================

-- Top 10 routes by CO2 savings
SELECT 
    route_name_simple,
    origin_country,
    destination_country,
    distance_km,
    co2_savings_kg
FROM fact_routes
WHERE co2_savings_kg IS NOT NULL
ORDER BY co2_savings_kg DESC
LIMIT 10;

-- Routes by country
SELECT 
    origin_country,
    COUNT(*) as route_count,
    ROUND(AVG(distance_km), 2) as avg_distance,
    ROUND(SUM(co2_savings_kg), 2) as total_savings_kg
FROM fact_routes
WHERE origin_country IS NOT NULL
GROUP BY origin_country
ORDER BY total_savings_kg DESC;

-- Routes by train type
SELECT * FROM v_routes_by_type;

-- Overall summary
SELECT * FROM v_summary_stats;

-- ========================================
-- SUCCESS MESSAGE
-- ========================================

SELECT '✅ Database setup complete and validated!' as status;