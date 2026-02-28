# ObRail Europe — API

FastAPI application providing REST API endpoints and a public web dashboard for European night and day train routes with CO₂ environmental impact analysis.

---

## Quick Start

> **Prerequisite**: Docker Desktop or WSL installed and running.

```bash
git clone <repo-url>
cd Obrail-MSPR
cp .env.example .env.docker
docker compose up --build -d
```

Then open http://localhost:8001

---

## Access Points

| Page | URL |
|------|-----|
| Dashboard | http://localhost:8001/ |
| Routes | http://localhost:8001/routes-page |
| Countries + Data Quality | http://localhost:8001/countries-page |
| API Docs (Swagger) | http://localhost:8001/api/docs |
| API Docs (ReDoc) | http://localhost:8001/api/redoc |
| Health Check | http://localhost:8001/health |

---

## API Endpoints

### Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/routes` | All routes (supports filters) |
| GET | `/api/routes/{id}` | Single route by ID |
| GET | `/api/routes/export` | Download all routes as CSV |

**Filters for `/api/routes`:**
- `country` — origin country code (e.g. `FR`, `DE`)
- `train_type` — `night` or `day`
- `limit` — max results, default `100`

### Countries
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/countries` | All countries with statistics |
| GET | `/api/countries/{code}` | Routes for a specific country |

### Emissions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/emissions/summary` | Overall CO₂ savings statistics |
| GET | `/api/emissions/top-routes` | Routes with highest CO₂ savings |

---

## Project Structure

```
api/
├── Dockerfile
├── main.py              # All endpoints and dashboard logic
├── database.py          # PostgreSQL connection
├── models.py            # Pydantic data models
├── requirements.txt
├── templates/
│   ├── Dashboard.html   # KPIs, emissions comparison, top routes
│   ├── Routes.html      # Routes browser with filters
│   └── Countries.html   # Territorial analysis + data quality monitor
└── tests/
    ├── conftest.py
    ├── test_health.py
    ├── test_dashboard.py
    ├── test_routes.py
    ├── test_countries.py
    └── test_emissions.py
```

---

## Environment Variables

Two env files are used:
- `.env` — local development (`localhost:5433`)
- `.env.docker` — Docker (`obrail_db:5432`)

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_DB` | Database name |
| `DATABASE_URL` | Full connection string |

---

## Running Tests

```bash
pip install pytest httpx
docker compose up -d
pytest api/tests/ -v
```

---

## Useful Docker Commands

```bash
# Start in background
docker compose up -d

# Rebuild after code changes
docker compose up --build

# View API logs
docker logs obrail_api -f

# Stop everything
docker compose down

# Check route count in DB
docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db -c "SELECT COUNT(*) FROM fact_routes;"
```

---

## Troubleshooting

**Port already in use** — kill it: `fuser -k 8001/tcp`

**Database connection error** — check containers are running: `docker ps`

**No data showing** — load the data: `python scripts/load_database.py`

**Template not found** — check capitalisation of filenames (`Dashboard.html` not `dashboard.html`)

---

*ObRail Europe — MSPR 2026*