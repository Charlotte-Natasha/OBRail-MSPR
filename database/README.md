# 🗄️ OBRail Europe — Documentation de la Base de Données

## Présentation

La base de données OBRail stocke les données relatives aux routes de trains de nuit européens ainsi que leur impact environnemental comparé à l'avion. Chaque enregistrement correspond à une route individuelle avec ses calculs d'émissions CO₂.

---

## Prérequis

- **PostgreSQL** 15+
- **Docker** & **Docker Compose** (recommandé)
- Ou une instance PostgreSQL locale

---

## Structure des fichiers

```
database/
├── init/
│   ├── 01_create_schema.sql   # Création des tables, index et vues
│   ├── 02_reference_data.sql  # Données de référence (pays, modes de transport, types de train)
│   └── 03_test.sql            # Requêtes de validation
```

---

## Lancement avec Docker

```bash
# Copier et configurer les variables d'environnement
cp .env.example .env

# Démarrer la base de données
docker compose up -d obrail_db

# Vérifier que la base est prête
docker logs obrail_postgres_db
```

Les fichiers dans `database/init/` sont exécutés **automatiquement** au premier démarrage, dans l'ordre alphabétique.

---

## Variables d'environnement

| Variable            | Description                        | Valeur par défaut   |
|---------------------|------------------------------------|---------------------|
| `POSTGRES_USER`     | Nom d'utilisateur PostgreSQL       | `obrail_user`       |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL            | —                   |
| `POSTGRES_DB`       | Nom de la base de données          | `obrail_db`         |
| `POSTGRES_PORT`     | Port exposé sur la machine hôte    | `5433`              |

---

## Schéma de la base de données

### Tables de dimension

| Table                  | Description                                              |
|------------------------|----------------------------------------------------------|
| `dim_countries`        | Pays européens (code ISO + nom)                          |
| `dim_transport_modes`  | Modes de transport avec facteur d'émission (gCO₂/pkm)   |
| `dim_train_types`      | Types de trains (`night`, `day`)                         |

### Table de faits

| Table          | Description                                                            |
|----------------|------------------------------------------------------------------------|
| `fact_routes`  | Routes individuelles avec distances, émissions CO₂ et économies       |

#### Clés étrangères de `fact_routes`

| Colonne                | Référence                            |
|------------------------|--------------------------------------|
| `origin_country`       | `dim_countries(country_code)`        |
| `destination_country`  | `dim_countries(country_code)`        |
| `train_type`           | `dim_train_types(type_code)`         |
| `train_mode_id`        | `dim_transport_modes(mode_id)`       |
| `plane_mode_id`        | `dim_transport_modes(mode_id)`       |

---

## Vues disponibles

| Vue                    | Description                                              |
|------------------------|----------------------------------------------------------|
| `v_savings_by_country` | Total des économies CO₂ par pays                         |
| `v_top_routes_savings` | Top 50 des routes (dédupliquées) par économies CO₂       |
| `v_summary_stats`      | Statistiques globales de la base                         |
| `v_routes_by_type`     | Nombre de routes et économies par type de train          |

---

## Validation de la base

Pour vérifier que tout est correctement initialisé :

```bash
# Se connecter à la base
psql -h localhost -p 5433 -U obrail_user -d obrail_db

# Lancer les tests
\i database/init/03_test.sql
```

Le script vérifie :
- L'existence de toutes les tables et vues
- Le chargement des données de référence
- Le bon fonctionnement des vues
- La création des index

---

## Connexion locale

```
Host     : localhost
Port     : 5433
Database : obrail_db
User     : obrail_user
```

> ⚠️ Le port `5433` est utilisé sur la machine hôte pour éviter les conflits avec une instance PostgreSQL locale sur le port `5432`.

---

## Accès depuis l'API

À l'intérieur du réseau Docker, l'API se connecte via :

```
postgresql://obrail_user:<password>@obrail_db:5432/obrail_db
```

---

## Sources des données d'émissions

| Mode de transport         | gCO₂/pkm | Source                                      |
|---------------------------|-----------|---------------------------------------------|
| Train de nuit / jour      | 14        | Back-on-Track 2022                          |
| Avion                     | 144       | Back-on-Track 2022                          |
| Avion (forçage radiatif)  | 389       | Back-on-Track 2022 (Radiative Forcing ×3.0) |
| Avion (SAF)               | 20        | Back-on-Track 2022                          |
| Voiture diesel            | 132       | Back-on-Track 2022                          |
| Car / Bus                 | 22        | Back-on-Track 2022                          |
| Voiture électrique (PV)   | 62        | Back-on-Track 2022                          |