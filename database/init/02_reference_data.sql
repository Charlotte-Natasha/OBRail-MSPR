/* =========================================================
   OBRAIL EUROPE - REFERENCE DATA
   Pre-populate dimension tables with known values
   ========================================================= */

-- ========================================
-- COUNTRIES
-- ========================================

INSERT INTO dim_countries (country_code, country_name) VALUES
('FR', 'France'),
('DE', 'Germany'),
('CH', 'Switzerland'),
('AT', 'Austria'),
('IT', 'Italy'),
('ES', 'Spain'),
('BE', 'Belgium'),
('NL', 'Netherlands'),
('GB', 'United Kingdom'),
('DK', 'Denmark'),
('SE', 'Sweden'),
('NO', 'Norway'),
('PL', 'Poland'),
('CZ', 'Czech Republic'),
('HU', 'Hungary'),
('RO', 'Romania'),
('BG', 'Bulgaria'),
('HR', 'Croatia'),
('SI', 'Slovenia'),
('SK', 'Slovakia'),
('LU', 'Luxembourg'),
('PT', 'Portugal'),
('GR', 'Greece'),
('FI', 'Finland'),
('EE', 'Estonia'),
('LV', 'Latvia'),
('LT', 'Lithuania')
ON CONFLICT (country_code) DO NOTHING;

-- ========================================
-- TRANSPORT MODES
-- ========================================

INSERT INTO dim_transport_modes (mode_name, gco2_per_pkm, source) VALUES
('Night Train', 14, 'Back-on-Track 2022'),
('Day Train', 14, 'Back-on-Track 2022'),
('Airplane', 144, 'Back-on-Track 2022'),
('Airplane (with RF)', 389, 'Back-on-Track 2022 (Radiative Forcing 3.0)'),
('Car (Diesel)', 132, 'Back-on-Track 2022'),
('Coach/Bus', 22, 'Back-on-Track 2022'),
('Electric Car (PV)', 62, 'Back-on-Track 2022'),
('Airplane (SAF)', 20, 'Back-on-Track 2022 (Sustainable Aviation Fuel)')
ON CONFLICT DO NOTHING;

-- ========================================
-- TRAIN TYPES
-- ========================================

INSERT INTO dim_train_types (type_code, type_name) VALUES
('night', 'Night Train'),
('day', 'Day Train')
ON CONFLICT (type_code) DO NOTHING;