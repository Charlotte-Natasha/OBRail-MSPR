-- DIM_COUNTRY
INSERT INTO dim_country (country_code, nom_country) VALUES
('FR', 'France'),
('DE', 'Allemagne'),
('ES', 'Espagne');

-- DIM_TYPE_TRAIN
INSERT INTO dim_type_train (id_type_train, type_train, nom_type_train) VALUES
(1, 'Jour', 'Train de jour'),
(2, 'Nuit', 'Train de nuit');

-- DIM_DATE
INSERT INTO dim_date (id_date, jour, mois, annee) VALUES
(20240101, 1, 1, 2024),
(20240102, 2, 1, 2024),
(20240103, 3, 1, 2024);
