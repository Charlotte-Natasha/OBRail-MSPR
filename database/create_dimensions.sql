-- Table des pays
CREATE TABLE dim_country (
  country_code VARCHAR(5) PRIMARY KEY,
  nom_pays VARCHAR(100)
);

-- Table des types de train
CREATE TABLE dim_type_train (
  id_type_train INT PRIMARY KEY,
  type_train VARCHAR(20)
);

-- Table de dates
CREATE TABLE dim_date (
  id_date INT PRIMARY KEY,
  jour INT,
  mois INT,
  annee INT
);
