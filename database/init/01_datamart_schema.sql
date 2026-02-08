/* =========================================================
   DATAMART CO2 - MSPR
   Schéma étoile décisionnel
   ========================================================= */

/* =========================
   TABLES DE DIMENSIONS
   ========================= */

/* Dimension pays */
CREATE TABLE dim_country (
    country_code VARCHAR(5) PRIMARY KEY,
    nom_country VARCHAR(100) NOT NULL
);

/* Dimension type de train */
CREATE TABLE dim_type_train (
    id_type_train INT PRIMARY KEY,
    type_train VARCHAR(20) NOT NULL,
    nom_type_train VARCHAR(50)
);

/* Dimension temps */
CREATE TABLE dim_date (
    id_date INT PRIMARY KEY,
    jour INT NOT NULL,
    mois INT NOT NULL,
    annee INT NOT NULL
);

/* =========================
   TABLE DE FAITS
   ========================= */

CREATE TABLE fact_co2 (
    id_fact_co2 INT PRIMARY KEY,
    co2 DECIMAL(10,2) NOT NULL,
    unit VARCHAR(10),
    data_source VARCHAR(100),

    country_code VARCHAR(5) NOT NULL,
    id_type_train INT NOT NULL,
    id_date INT NOT NULL,

    CONSTRAINT fk_fact_country
        FOREIGN KEY (country_code)
        REFERENCES dim_country(country_code),

    CONSTRAINT fk_fact_type_train
        FOREIGN KEY (id_type_train)
        REFERENCES dim_type_train(id_type_train),

    CONSTRAINT fk_fact_date
        FOREIGN KEY (id_date)
        REFERENCES dim_date(id_date)
);
