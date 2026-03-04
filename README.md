# ObRail Europe — Plateforme d'Analyse des Émissions CO2

ObRail Europe est un projet MSPR Bloc E6.1 qui collecte et analyse les données environnementales des réseaux ferroviaires européens. La plateforme extrait des données horaires GTFS depuis plusieurs opérateurs européens, calcule les économies CO2 par rapport à l'avion en utilisant les facteurs d'émission Back-on-Track 2022, et expose les résultats via une API REST et un tableau de bord public.

---

## Prérequis

- Python 3.10+
- Java 17 ou 21 (requis par PySpark)
- Docker Desktop

---

## Variables d'Environnement

Deux fichiers `.env` sont requis à la racine du projet. Des modèles sont fournis :

-  `.env` Utilisé par le pipeline ETL en exécution locale.
-  `.env.docker` Utilisé par le conteneur API dans Docker. L'hôte de la base de données doit être le nom du service Docker (`obrail_db`) et non `localhost`.

---

## Données GTFS

Les données GTFS ne sont pas committées dans ce dépôt en raison de leur taille. Téléchargez chaque source et placez-la dans le bon sous-dossier de `data/raw/` avant de lancer le pipeline.

**Trains de jour** → `data/raw/day/`
- France (SNCF) : [transport.data.gouv.fr](https://transport.data.gouv.fr/resources/67595?locale=en)
- Allemagne (VBB) : [unternehmen.vbb.de](https://unternehmen.vbb.de/digitale-services/datensaetze/)
- Suisse (SBB) : [gtfs.geops.ch](https://gtfs.geops.ch/#feeds)
- Danemark (DSB) : [eu.data.public-transport.earth](https://eu.data.public-transport.earth/)

**Trains de nuit** → `data/raw/night/`
- ÖBB Nightjet : [data.oebb.at](https://data.oebb.at/de/datensaetze~soll-fahrplan-gtfs~)
- DB Fernverkehr : [gtfs.de](https://gtfs.de/en/feeds/de_fv/)
- Back-on-Track : [github.com/Back-on-Track-eu](https://github.com/Back-on-Track-eu/night-train-data/tree/main)

**Données CO2** → placer `Emissions.ods` dans `data/raw/co2/`

---

## Lancer le Projet

### 1. Vérifier les dépendances et l'environnement

```bash
python setup.py
```

Vérifie que Python, Java, tous les packages requis et la structure des dossiers sont correctement en place. Corrigez les problèmes signalés avant de continuer.

### 2. Vérifier la configuration et les données GTFS

```bash
python config/settings.py
```

Affiche un résumé complet de la configuration, crée les répertoires de sortie manquants, et valide quels dossiers GTFS sont présents et peuplés. Si un dossier apparaît comme manquant ou vide, téléchargez les données correspondantes avant de continuer.

### 3. Démarrer les services Docker

```bash
docker compose up -d --build
```

Lance la base de données PostgreSQL et l'application FastAPI. Le schéma de la base de données est initialisé automatiquement au premier démarrage.

### 4. Lancer le pipeline ETL complet

```bash
python main.py
```

Exécute les six phases en séquence — extraction nuit et jour, chargement des références CO2, transformation, calcul CO2, et chargement en base. La progression est affichée dans le terminal et les logs détaillés sont sauvegardés dans `logs/`.

Une fois le pipeline terminé, le tableau de bord est disponible sur **http://localhost:8001** et la documentation API sur **http://localhost:8001/api/docs**.

---

## Lancer les Tests

```bash
pytest api/tests/ -v
```

Nécessite que les conteneurs Docker soient actifs.

---

## Notes

- `logs/` est exclu de git — les logs sont générés automatiquement à chaque exécution du pipeline
- `.env` et `.env.docker` sont exclus de git — ne committez jamais vos identifiants dans le dépôt

---

## Contributeurs

ObRail Europe Data Team — MSPR Bloc E6.1 — EPSI 2026