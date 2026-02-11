# Base de Données ObRail Europe

## ⚠️ CHANGEMENTS IMPORTANTS - LIRE ATTENTIVEMENT

### Pourquoi le Schéma Précédent Ne Fonctionnait Pas

**Problème Principal:**
Le schéma initial (`fact_co2`) était conçu pour stocker **des données agrégées par pays et date**, mais notre pipeline ETL produit **des données détaillées route par route**.

#### Ce que le schéma initial stockait:
```
Exemple:
- France, Train de jour, 01/01/2024 → 120.5 kg CO2
- Allemagne, Train de nuit, 02/01/2024 → 95.2 kg CO2
```

**Format:** Agrégation par pays/type/date  
**Structure:** Une ligne = émissions totales pour un pays à une date donnée

#### Ce que notre ETL produit réellement:
```
Exemple:
- Paris → Berlin, 1054 km, Train: 14.76 kg, Avion: 151.78 kg, Économie: 137 kg
- Vienne → Paris, 1034 km, Train: 14.48 kg, Avion: 148.90 kg, Économie: 134 kg
```

**Format:** Détail route par route  
**Structure:** Une ligne = une route spécifique avec ses calculs CO2

#### Pourquoi c'est incompatible:

**Le schéma initial ne pouvait PAS stocker:**
- ❌ Les villes d'origine et destination
- ❌ La distance de chaque route
- ❌ Les émissions train vs avion par route
- ❌ Les économies CO2 par route spécifique

**Notre CSV contient 4387 routes avec ces informations!**

---

## ✅ Nouveau Schéma - Solution Correcte

### Structure Actuelle

#### Tables de Dimensions (Inchangées)
```sql
dim_countries       -- Pays (FR, DE, CH, etc.)
dim_transport_modes -- Modes de transport (train, avion, voiture)
dim_train_types     -- Types de trains (jour, nuit)
```

#### Table de Faits (NOUVELLE)
```sql
fact_routes         -- Routes individuelles avec impact environnemental
```

### Colonnes de fact_routes

| Colonne | Type | Description |
|---------|------|-------------|
| route_id | SERIAL | Identifiant unique |
| route_name | VARCHAR | Nom de la route |
| origin | VARCHAR | Ville de départ |
| destination | VARCHAR | Ville d'arrivée |
| origin_country | VARCHAR | Pays de départ (FK → dim_countries) |
| destination_country | VARCHAR | Pays d'arrivée (FK → dim_countries) |
| distance_km | DECIMAL | Distance en kilomètres |
| train_type | VARCHAR | Type de train (jour/nuit) |
| train_co2_kg | DECIMAL | Émissions CO2 du train (kg) |
| plane_co2_kg | DECIMAL | Émissions CO2 de l'avion (kg) |
| co2_savings_kg | DECIMAL | Économies CO2 (avion - train) |
| savings_percent | DECIMAL | Pourcentage d'économie |
| emission_source | VARCHAR | Source des données (Back-on-Track 2022) |
| calculation_date | DATE | Date du calcul |

### Exemple de Données

```sql
INSERT INTO fact_routes (origin, destination, origin_country, destination_country, 
                        distance_km, train_co2_kg, plane_co2_kg, co2_savings_kg)
VALUES 
('Paris', 'Berlin', 'FR', 'DE', 1054, 14.76, 151.78, 137.02),
('Vienne', 'Paris', 'AT', 'FR', 1034, 14.48, 148.90, 134.42);
```

---

## 📊 Différences Clés

### Ancien Schéma (Incorrect pour ce projet)
```
✗ Agrégation: Une valeur CO2 par pays/date
✗ Granularité: Niveau pays
✗ Utilité: Suivre les émissions nationales totales
✗ Problème: Ne peut pas montrer quelles routes économisent le plus de CO2
```

### Nouveau Schéma (Correct)
```
✓ Détaillé: Chaque route est une ligne séparée
✓ Granularité: Niveau route
✓ Utilité: Comparer train vs avion route par route
✓ Avantage: Peut identifier les routes prioritaires pour investissement
```

---

## 🎯 Objectifs du Projet

Notre projet doit démontrer:
1. **Quelles routes** ferroviaires de nuit existent en Europe
2. **Combien de CO2** chaque route économise vs avion
3. **Quelles routes** ont le plus grand impact environnemental
4. **Quels pays** bénéficient le plus des trains de nuit

**Pour cela, nous avons besoin de données détaillées route par route, pas d'agrégations!**

---

## 🔄 Processus ETL Complet

### Phase 1: EXTRACTION
```
Sources: Fichiers GTFS (horaires de trains)
Scripts: night_trains.py, day_trains.py
Sortie: CSV avec routes extraites
```

### Phase 2: TRANSFORMATION
```
Entrée: Routes brutes
Scripts: clean_routes.py, calculate_co2.py
Traitement:
  - Nettoyage des données
  - Ajout des pays
  - Calcul des distances
  - Calcul CO2 train vs avion
Sortie: environmental_impact.csv (4387 routes)
```

### Phase 3: CHARGEMENT (Ce fichier)
```
Entrée: environmental_impact.csv
Script: load_database.py
Traitement:
  - Lecture du CSV
  - Insertion dans fact_routes
  - Validation des données
Sortie: Base PostgreSQL prête pour API
```

---

## 📁 Organisation des Fichiers

### Structure Correcte
```
database/init/
├── 01_create_schema.sql          ← Crée les tables
├── 02_insert_reference_data.sql  ← Ajoute pays & modes transport
└── 03_test.sql                   ← Vérifie que tout fonctionne
```

### Fichiers à Supprimer (Obsolètes)
```
❌ create_dimensions.sql     -- Doublon, pas utilisé
❌ create_fact.sql           -- Doublon, pas utilisé
❌ datamart_schema.sql       -- Vide, pas utilisé
❌ 01_datamart_schema.sql    -- Ancien schéma incorrect
❌ 02_insert_dimensions.sql  -- Ancien format
❌ 03_insert_fact.sql        -- Données exemple incorrectes
```

**Raison:** Docker exécute seulement les fichiers numérotés 01_, 02_, 03_  
Les autres fichiers ne sont jamais exécutés mais créent de la confusion.

---

## 🚀 Utilisation

### Démarrage Initial
```bash
# Démarrer PostgreSQL dans Docker
docker-compose up -d

# Vérifier que les tables sont créées
docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db -c "\dt"

# Vous devriez voir:
# - dim_countries
# - dim_transport_modes
# - dim_train_types
# - fact_routes
```

### Charger les Données
```bash
# Exécuter le pipeline ETL complet
python scripts/main.py

# Ou juste la phase de chargement
python scripts/load_database.py
```

### Vérification
```bash
# Compter les routes chargées
docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db -c "SELECT COUNT(*) FROM fact_routes;"

# Voir les statistiques
docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db -c "SELECT * FROM v_summary_stats;"
```

---

## 📈 Requêtes Utiles

### Top 10 Routes par Économies CO2
```sql
SELECT 
    route_name_simple,
    origin_country,
    destination_country,
    distance_km,
    co2_savings_kg
FROM fact_routes
ORDER BY co2_savings_kg DESC
LIMIT 10;
```

### Économies Totales par Pays
```sql
SELECT * FROM v_savings_by_country;
```

### Statistiques Globales
```sql
SELECT * FROM v_summary_stats;
```

---

## 🎓 Pour le MSPR

### Ce que cette base de données démontre:

1. **Compétence ETL Complète**
   - Extract: Lecture de sources hétérogènes (GTFS)
   - Transform: Nettoyage et calculs complexes
   - Load: Insertion dans base de données relationnelle

2. **Modélisation Dimensionnelle**
   - Dimensions: Pays, modes de transport
   - Faits: Routes avec métriques mesurables
   - Relations: Clés étrangères correctes

3. **Qualité des Données**
   - Validation: Pas de valeurs nulles critiques
   - Index: Performance optimisée
   - Vues: Requêtes analytiques pré-calculées

4. **Impact Environnemental Mesurable**
   - 4387 routes analysées
   - Économies CO2 calculées route par route
   - Recommandations data-driven possibles

---

## ❓ Questions Fréquentes

### Pourquoi pas d'agrégation par pays?
**Réponse:** On peut l'obtenir avec une requête SQL sur fact_routes!
```sql
SELECT origin_country, SUM(co2_savings_kg) 
FROM fact_routes 
GROUP BY origin_country;
```
Mais on ne peut PAS faire l'inverse (retrouver les routes depuis des données agrégées).

### Pourquoi tant de colonnes dans fact_routes?
**Réponse:** Chaque colonne correspond aux données de notre CSV. On stocke tout pour permettre des analyses variées.

### Les vues (views) c'est quoi?
**Réponse:** Des requêtes SQL sauvegardées. Elles permettent d'accéder facilement aux statistiques sans réécrire les requêtes complexes.

---

## ✅ Résumé - Points Clés

| Aspect | Ancien Schéma | Nouveau Schéma |
|--------|--------------|----------------|
| **Granularité** | Par pays/date | Par route |
| **Données** | Agrégées | Détaillées |
| **Nombre lignes** | ~100 | ~4387 |
| **Utilité** | Suivi national | Analyse route par route |
| **Compatible CSV** | ❌ Non | ✅ Oui |
| **Objectif MSPR** | ❌ Non aligné | ✅ Parfait |

**Le nouveau schéma correspond exactement aux besoins du projet et aux données produites par le pipeline ETL.**

