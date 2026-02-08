# Datamart CO2 - Train

## Contenu

- `create_dimensions.sql` : contient les tables de dimensions
- `create_fact.sql` : contient la table de faits
- `datamart_schema.sql` : structure globale du datamart

## Objectif

Ce datamart est destiné à être alimenté par les données issues des sources opérationnelles après un processus d’ETL (extraction, transformation, chargement).

Il permettra d’analyser les émissions de CO2 par type de train, pays et date.


🔄 Processus ETL (simplifié)

Les données intégrées dans le datamart sont issues d’un processus d’ETL simplifié.
Les données sources hétérogènes (pays, type de train, émissions de CO₂) ont été harmonisées afin d’utiliser des formats communs (codes pays, unités de mesure, granularité temporelle).
Les données transformées sont ensuite chargées dans les tables de dimensions puis dans la table de faits, conformément au schéma étoile défini.