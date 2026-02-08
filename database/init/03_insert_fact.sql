INSERT INTO fact_co2 (
  id_fact_co2,
  co2,
  unit,
  data_source,
  country_code,
  id_type_train,
  id_date
) VALUES
(1, 120.50, 'kg', 'Source européenne', 'FR', 1, 20240101),
(2, 80.30,  'kg', 'Source européenne', 'FR', 2, 20240101),
(3, 150.00, 'kg', 'Source européenne', 'DE', 1, 20240102),
(4, 95.20,  'kg', 'Source européenne', 'DE', 2, 20240102),
(5, 110.10, 'kg', 'Source européenne', 'ES', 1, 20240103),
(6, 70.40,  'kg', 'Source européenne', 'ES', 2, 20240103);
