-- Table de faits pour les émissions de CO2
CREATE TABLE fact_co2 (
  id_fact_co2 INT PRIMARY KEY,
  country_code VARCHAR(5),
  id_type_train INT,
  id_date INT,
  co2 DECIMAL(10,2),
  unit VARCHAR(10),
  data_source VARCHAR(100),
  FOREIGN KEY (country_code) REFERENCES dim_country(country_code),
  FOREIGN KEY (id_type_train) REFERENCES dim_type_train(id_type_train),
  FOREIGN KEY (id_date) REFERENCES dim_date(id_date)
);
