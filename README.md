# 🚂 ObRail Europe - CO2 Emissions Analysis Platform

A comprehensive ETL (Extract, Transform, Load) pipeline for analyzing CO2 emissions across European rail networks, comparing train vs. plane travel, and providing data-driven insights through a REST API.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Data Sources](#data-sources)
- [Requirements](#requirements)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [API Endpoints](#api-endpoints)
- [Database Architecture](#database-architecture)

---

## 🎯 Overview

ObRail Europe is an MSPR project that collects and analyzes environmental data about European rail networks. The platform:

- Extracts GTFS (General Transit Feed Specification) data from multiple European countries
- Integrates CO2 emission reference data
- Transforms heterogeneous data sources into a unified format
- Loads data into a PostgreSQL datamart for analysis
- Provides REST API endpoints for querying routes and CO2 comparisons

---

## ✨ Features

- **Multi-country GTFS Data**: Covers Denmark, France, Germany, Switzerland
- **Night Train Analysis**: Dedicated processing for night routes (OBB, SNCF, etc.)
- **CO2 Emissions Tracking**: Compares train vs. plane emissions for routes
- **Star Schema Datamart**: Optimized for dimensional analysis
- **REST API**: Query routes, analyze CO2 savings, and compare transportation modes
- **Containerized**: Docker Compose setup for easy deployment
- **Data Quality Checks**: CSV validation and cleaning pipeline

---

## 📁 Project Structure

```
Obrail-MSPR/
├── api/                          # Application FastAPI (micro‑service)
│   ├── main.py                  # Routes et endpoints de l’API
│   ├── models.py                # Modèles SQLAlchemy
│   ├── database.py              # Configuration de la BDD
│   ├── requirements.txt         # dépendances spécifiques à l’API
│   ├── Dockerfile               # image Docker pour le service
│   ├── README.md                # doc de l’API
│   ├── tests/                   # tests pytest de l’API
│   │   ├── conftest.py
│   │   ├── test_countries.py
│   │   ├── test_dashboard.py
│   │   ├── test_emissions.py
│   │   ├── test_health.py
│   │   └── test_routes.py
│   ├── templates/              # pages HTML statiques
│   └── __init__.py
├── config/
│   └── settings.py              # Configuration centrale (chargement .env)
├── data/
│   ├── raw/                     # Données brutes
│   │   ├── day/                 # GTFS train de jour par pays
│   │   ├── night/               # GTFS train de nuit
│   │   └── co2/                 # Références émissions CO₂
│   ├── extracted/               # Routes extraites (CSV)
│   └── transformed/             # Données nettoyées et traitées
├── database/
│   ├── init/                    # Scripts SQL d’initialisation
│   │   ├── 01_create_schema.sql
│   │   ├── 02_reference_data.sql
│   │   └── 03_test.sql
│   └── README.md                # Documentation du schéma
├── scripts/                      # Scripts ETL Python
│   ├── day_trains.py            # Extraction routes de jour
│   ├── night_trains.py          # Extraction routes de nuit
│   ├── clean_routes.py          # Pipeline de nettoyage
│   ├── emissions.py             # Logique de calcul CO₂
│   └── calculate_co2.py         # Utilitaires de calcul CO₂

├── logs/                         # Journaux d’exécution
├── main.py                       # Orchestrateur ETL principal
├── setup.py                      # Validation de l’environnement
├── docker-compose.yml            # Configuration des services Docker
├── requirements.txt              # Dépendances Python globales
├── .env/.env.docker             # exemples de variables d’environnement
└── README.md                     # Ce document
```

---

## 📊 Data Sources

### GTFS (General Transit Feed Specification) Data

#### **Day Train Routes**

- **Denmark**: [EU Public Transport Data Portal](https://eu.data.public-transport.earth/)
- **France (SNCF)**: [French Transport Data Portal](https://transport.data.gouv.fr/resources/67595?locale=en)
- **Germany (VBB)**: [VBB Digital Services - Datasets](https://unternehmen.vbb.de/digitale-services/datensaetze/)
- **Switzerland**: [GTFS Data from Geops](https://gtfs.geops.ch/#feeds)

#### **Night Train Routes**

- **OBB Network Routes**: [ÖBB Open Data - Night Train Network](https://data.oebb.at/de/datensaetze~streckennetz-nachtzuege~)
- **OBB Timetable Data**: [ÖBB Open Data - SOLL Fahrplan GTFS](https://data.oebb.at/de/datensaetze~soll-fahrplan-gtfs~)
- **LongDistance Rail Germany**: [GTFS.de - German Fernverkehr](https://gtfs.de/en/feeds/de_fv/)
- **Deutsche Bahn**: Unofficial Deutsche Bahn Fernverkehr (German Railways Long-Distance Trains) Timetable GTFS Feed (2018-12-09 to 2019-12-14)
- **Night Train Research**: [Back-on-Track EU - Night Train Data](https://github.com/Back-on-Track-eu/night-train-data/tree/main)

### CO2 Emissions Reference Data

- **EEA Transport Emissions**: [European Environment Agency Data Hub](https://www.eea.europa.eu/en/datahub?q=transport%20emmisions&size=n_10_n&filters%5B0%5D%5Bfield%5D=issued.date&filters%5B0%5D%5Bvalues%5D%5B0%5D=All%20time&filters%5B0%5D%5Btype%5D=any)
- **Energy Data**: [Our World in Data - Energy Data](https://github.com/owid/energy-data)
- **EU Energy Statistics**: [EU Energy Statistical Pocketbook & Country Datasheets](https://energy.ec.europa.eu/data-and-analysis/eu-energy-statistical-pocketbook-and-country-datasheets_en)

---

## 📋 Requirements

### System Requirements

- **Python**: 3.10 or higher
- **Java**: 17 or Java 21 (required by PySpark)
- **Docker**: (Optional, for containerized deployment)

### Python Dependencies

See [requirements.txt](requirements.txt) for the full list. Key packages:

- **pyspark** ≥ 3.5.0 - Distributed data processing
- **pandas** ≥ 2.1.0 - Data manipulation
- **fastapi** ≥ 0.109.0 - REST API framework
- **sqlalchemy** ≥ 2.0.0 - ORM for database
- **psycopg2** ≥ 2.9.9 - PostgreSQL adapter
- **requests** ≥ 2.31.0 - HTTP library for data fetching

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Obrail-MSPR
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Database (Docker)

```bash
docker compose up -d --build
```

This starts:

- PostgreSQL database on `localhost:5432`
- FastAPI application on `localhost:8000`

### 4. Initialize Database Schema

```bash
# Connect to the running PostgreSQL container and run initialization scripts
psql -h localhost -U admin -d obrail_db -f database/init/01_datamart_schema.sql
psql -h localhost -U admin -d obrail_db -f database/init/02_insert_dimensions.sql
psql -h localhost -U admin -d obrail_db -f database/init/03_insert_fact.sql
```

---

## ▶️ Getting Started

### Run the Complete ETL Pipeline

```bash
python main.py
```

This executes all phases in sequence:

1. **Extract Phase**: Extracts night and day routes from GTFS data
2. **Transform Phase**: Cleans, validates, and transforms data
3. **Load Phase**: Loads data into the PostgreSQL datamart
4. **Report Phase**: Generates summary statistics

### Run Individual Components

```bash
# Extract night train routes
python scripts/night_trains.py

# Extract day train routes
python scripts/day_trains.py

# Clean and transform routes
python scripts/clean_routes.py

# Calculate CO2 emissions
python scripts/calculate_co2.py
```

### Validate Project Setup

```bash
python setup.py
```

Checks Python version, dependencies, folder structure, and GTFS data availability.

---

## 🔌 API Endpoints

The FastAPI application provides the following endpoints:

### Health Check

```
GET /health
```

Returns database connection status.

### Get All Routes

```
GET /routes
```

Returns all available routes in the database.

### Get Routes by Origin

```
GET /routes/{origin}
```

Returns routes starting from a specific city.

**Example:**

```
GET /routes/Paris
```

### CO2 Comparison Analysis

```
GET /comparison/{route_id}
```

Returns CO2 emissions for train vs. plane and calculated savings.

**Example Response:**

```json
{
  "route": "Paris-Berlin",
  "train_kg_co2": 45.5,
  "plane_kg_co2": 180.2,
  "savings_kg": 134.7,
  "source": "EEA"
}
```

---

## 🗄️ Database Architecture

### Star Schema Design

The datamart uses a **dimensional (star) schema** optimized for OLAP analysis:

#### Dimensions

- **dim_country**: Country codes and names
- **dim_type_train**: Train types (day, night, etc.)
- **dim_date**: Time dimension (year, month, day)

#### Fact Table

- **fact_co2**: CO2 emissions measurements with foreign keys to all dimensions

### Schema Initialization

See [database/README.md](database/README.md) for detailed schema documentation and [database/init/](database/init/) for SQL scripts.

---

## 📝 Notes

- Data quality is ensured through CSV validation and cleaning pipelines
- Configuration is centralized in [config/settings.py](config/settings.py)
- Logs are written to the `logs/` directory
- Use Python dotenv for secure credential management (see `.env.example`)

---

## 📄 License

[Your License Here]

## 👥 Contributors

ObRail Europe Data Team (MSPR Project)
