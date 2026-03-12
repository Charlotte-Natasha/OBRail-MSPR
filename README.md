# ObRail Europe — Plateforme d'Analyse des Émissions CO2

**ObRail Europe** est un projet MSPR (Bloc E6.1) visant à collecter et analyser les données environnementales des réseaux ferroviaires européens.

La plateforme :

- extrait des données horaires GTFS depuis plusieurs opérateurs,
- calcule les économies de CO2 par rapport à l'avion en utilisant les facteurs d'émission _Back-on-Track 2022_,
- expose les résultats via une API REST et un tableau de bord public.

---

## 🛠️ Prérequis

Assurez‑vous que votre machine possède :

- **Python 3.10+**
- **Java 17 ou 21** (nécessaire pour PySpark utilisé dans le traitement des données)
- **Docker Desktop** (pour les services PostgreSQL et API)

> ⚠️ Vérifiez également que les variables d'environnement sont définies (voir ci‑dessous).

---

## 🔐 Variables d'environnement

Deux fichiers `.env` doivent être créés à la racine du projet. Des modèles sont fournis dans le dépôt.

| Fichier       | Usage                                                                  |
| ------------- | ---------------------------------------------------------------------- |
| `.env`        | Pipeline ETL local                                                     |
| `.env.docker` | Conteneur API Docker (le service DB s'appelle `obrail_db` dans Docker) |

---

## 📂 Sources de données GTFS

Les données GTFS ne sont **pas** commitées en raison de leur volume. Téléchargez chaque jeu et placez-le dans le sous‑dossier correspondant sous `data/raw/`.

- **Trains de jour**
  - France (SNCF) – [transport.data.gouv.fr](https://transport.data.gouv.fr)
  - Eurostar International – (liaisons GB/FR/BE)
  - Allemagne (VBB) – [unternehmen.vbb.de](https://unternehmen.vbb.de)
  - Suisse (SBB) – [gtfs.geops.ch](https://gtfs.geops.ch)
  - Danemark (DSB) – [data.public-transport.earth](https://eu.data.public-transport.earth)

- **Trains de nuit**
  - ÖBB Nightjet – [data.oebb.at](https://data.oebb.at)
  - Long Distance Rail – [gtfs.de](https://gtfs.de) (DB Fernverkehr)
  - Open Mobility Data – [mobilitydatabase.org](https://mobilitydatabase.org)

- **CO₂**
  Emissions.ods : Le référentiel des facteurs d'émission est basé sur les études de l'ICCT et du réseau Back-on-Track. Le fichier source peut être consulté/téléchargé via le portail de données de [Back-on-track](https://www.google.com/search?q=https://back-on-track.eu/the-carbon-footprint-of-night-trains/) .

Données CO₂ : placez le fichier `Emissions.ods` dans `data/raw/co2/`.

> 💡 Pour un démarrage rapide, téléchargez l’archive [data/raw zip](https://github.com/Charlotte-Natasha/OBRail-MSPR/releases/download/v1.0.0/raw.zip) et extrayez‑la dans `data/raw/`.

---

## 🚀 Démarrage rapide

1. **Vérifier l'environnement**  
   Exécutez le script de configuration pour valider Python, Java et les dépendances :

   ```bash
   python setup.py
   ```

2. **Valider les sources GTFS**  
   Assurez‑vous que tous les dossiers de `data/raw/` sont correctement peuplés :

   ```bash
   python config/settings.py
   ```

3. **Lancer les services Docker**  
   Démarre PostgreSQL et l’application FastAPI :

   ```bash
   docker compose up -d --build
   ```

4. **Exécuter le pipeline ETL complet**  
   Extraction, transformation, calcul CO₂ puis chargement :
   ```bash
   python main.py
   ```

Une fois terminé, ouvrez :

- Tableau de bord : http://localhost:8001
- Documentation de l’API : http://localhost:8001/api/docs

---

## 🧪 Tests

Lancez les tests unitaires et d’intégration :

```bash
pytest api/tests/ -v
```

> ⚠️ Les conteneurs Docker doivent être actifs pour que les tests d’API passent.

---

## 🧑‍💻 Contributeurs

ObRail Europe Data Team — MSPR Bloc E6.1 — EPSI 2026
