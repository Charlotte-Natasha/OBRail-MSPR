# ObRail Europe API

FastAPI application providing REST API endpoints and web dashboard for European night train routes with environmental impact analysis.

## 🚀 Features

### REST API Endpoints (JSON)
- **GET /api/routes** - Get all routes with optional filters
- **GET /api/routes/{id}** - Get specific route by ID
- **GET /api/countries** - Get all countries with statistics
- **GET /api/countries/{code}** - Get routes for specific country
- **GET /api/emissions/summary** - Get overall CO₂ s
- **GET /api/emissions/top-routes** - Get routes with highest savings

### Web Dashboard (HTML)
- **/** - Main dashboard with statistics and charts
- **/routes-page** - Browse routes with filters
- **/countries-page** - Country statistics overview

### Automatic Documentation
- **/api/docs** - Swagger UI (interactive API documentation)
- **/api/redoc** - ReDoc (alternative documentation)

## 📁 Project Structure

```
api/
├── __init__.py          # Package initialization
├── main.py              # FastAPI application (all endpoints)
├── database.py          # PostgreSQL connection
├── models.py            # Pydantic data models
├── requirements.txt     # Python dependencies
├── templates/           # HTML templates (Jinja2)
│   ├── dashboard.html   # Main dashboard
│   ├── routes.html      # Routes browsing page
│   └── countries.html   # Countries overview page
└── static/              # Static files (CSS, JS, images) - optional
```

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.8+
- PostgreSQL database (running in Docker)
- Database loaded with route data

### Step 1: Install Dependencies

```bash
# From project root
pip install -r api/requirements.txt
```

Or if using the requirements from project root:
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment

Make sure your `.env` file has correct database credentials:

```env
# Database connection
POSTGRES_USER=obrail_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=obrail_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

# Or full DATABASE_URL
DATABASE_URL=postgresql://obrail_user:password@localhost:5433/obrail_db
```

### Step 3: Verify Database

Make sure PostgreSQL is running and has data:

```bash
# Check Docker container
docker ps | grep obrail

# Verify tables exist
docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db -c "\dt"

# Check data exists
docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db -c "SELECT COUNT(*) FROM fact_routes;"
```

## 🚀 Running the API

### Development Mode (with auto-reload)

```bash
# Navigate to api folder
cd api/

# Start server
uvicorn main:app --reload

# Or from project root
uvicorn api.main:app --reload
```

### Production Mode

```bash
# Without auto-reload, on specific port
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Access the Application

Once running, access:

- **Dashboard**: http://localhost:8000/
- **API Docs**: http://localhost:8000/api/docs
- **Routes Page**: http://localhost:8000/routes-page
- **Countries Page**: http://localhost:8000/countries-page

## 📊 Using the API

### Example API Requests

**Get all routes:**
```bash
curl http://localhost:8000/api/routes
```

**Get routes from France:**
```bash
curl http://localhost:8000/api/routes?country=FR
```

**Get night trains only:**
```bash
curl http://localhost:8000/api/routes?train_type=night
```

**Get specific route:**
```bash
curl http://localhost:8000/api/routes/123
```

**Get emissions summary:**
```bash
curl http://localhost:8000/api/emissions/summary
```

**Get top routes:**
```bash
curl http://localhost:8000/api/emissions/top-routes?limit=10
```

### Response Format

All API endpoints return JSON:

```json
{
  "total": 4387,
  "routes": [
    {
      "route_id": 1,
      "route_name_simple": "Paris → Berlin",
      "origin": "Paris",
      "destination": "Berlin",
      "origin_country": "FR",
      "destination_country": "DE",
      "distance_km": 1054.0,
      "co2_savings_kg": 137.02
    }
  ]
}
```

## 🎨 Dashboard Features

### Main Dashboard
- **Summary Statistics**: Total routes, countries, CO₂ saved
- **Charts**: Top routes and country comparisons (Chart.js)
- **Top 10 Table**: Routes with highest savings

### Routes Page
- **Browse all routes** with pagination
- **Filter by country** (dropdown)
- **Filter by train type** (night/day)
- **Responsive cards** with route details

### Countries Page
- **Statistics table** with all countries
- **Sortable columns** (route count, savings, distance)
- **Quick view links** to country-specific routes

## 🔧 Troubleshooting

### Port Already in Use
```bash
# Change port
uvicorn main:app --port 8001
```

### Database Connection Error
```bash
# Verify PostgreSQL is running
docker ps

# Check .env credentials
cat .env

# Test connection manually
docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db
```

### No Data Showing
```bash
# Verify data exists in database
docker exec -it obrail_postgres_db psql -U obrail_user -d obrail_db -c "SELECT COUNT(*) FROM fact_routes;"

# If count is 0, run load script
python scripts/load_database.py
```

### Template Not Found
```bash
# Make sure you're running from correct directory
cd api/
uvicorn main:app --reload

# Or specify full path
uvicorn api.main:app --reload
```

## 📚 API Documentation

### Automatic Documentation

FastAPI automatically generates interactive documentation:

- **Swagger UI**: http://localhost:8000/api/docs
  - Interactive, try endpoints directly
  - See request/response examples
  - Test with your data

- **ReDoc**: http://localhost:8000/api/redoc
  - Alternative documentation style
  - Better for reading/printing

### Query Parameters

Most endpoints support query parameters:

**Pagination:**
- `limit`: Maximum results (default 100)

**Filters:**
- `country`: Filter by country code (e.g., FR, DE)
- `train_type`: Filter by type (night, day)

**Example:**
```
/api/routes?country=FR&train_type=night&limit=50
```

## 🎓 For MSPR Presentation

### What to Demonstrate

1. **Complete ETL Pipeline**:
   - GTFS → Extract → Transform → PostgreSQL → API → Dashboard

2. **RESTful API Design**:
   - Show /api/docs
   - Demonstrate filtering
   - Explain JSON responses

3. **Professional Dashboard**:
   - Open main dashboard
   - Show interactive charts
   - Filter routes by country

4. **Technical Skills**:
   - FastAPI (modern Python framework)
   - SQLAlchemy (database ORM)
   - Jinja2 (template engine)
   - Bootstrap (responsive design)
   - Chart.js (data visualization)

### Key Talking Points

- "We use FastAPI for its automatic documentation and modern async capabilities"
- "Bootstrap ensures our dashboard is responsive and professional"
- "Chart.js provides interactive visualizations of CO₂ savings"
- "All endpoints return JSON for easy integration with other applications"

## 🐳 Docker Integration (Optional)

To run API in Docker alongside database:

Uncomment the `obrail_api` service in `docker-compose.yml`:

```yaml
obrail_api:
  build: .
  container_name: obrail_api_service
  depends_on:
    obrail_db:
      condition: service_healthy
  env_file:
    - .env
  ports:
    - "8000:8000"
  networks:
    - obrail_network
```

Then:
```bash
docker-compose up -d
```

## 📝 Notes

- **Database must be loaded** before running API
- **Run from api/ directory** or use full module path
- **Environment variables** must be set in .env
- **Port 8000** is default (change if needed)
- **Auto-reload** only for development (--reload flag)

## 🆘 Support

If you encounter issues:

1. Check database is running: `docker ps`
2. Verify data loaded: `SELECT COUNT(*) FROM fact_routes`
3. Check logs: `uvicorn` output shows errors
4. Verify .env file: Database credentials correct
5. Try API docs: http://localhost:8000/api/docs (shows errors)

## ✅ Success Checklist

- [ ] PostgreSQL running in Docker
- [ ] Database tables created (4 tables)
- [ ] Data loaded into fact_routes
- [ ] Dependencies installed (pip install -r requirements.txt)
- [ ] .env file configured
- [ ] API starts without errors (uvicorn main:app --reload)
- [ ] Dashboard loads (http://localhost:8000/)
- [ ] API docs accessible (http://localhost:8000/api/docs)
- [ ] Routes show in dashboard
- [ ] Charts display correctly


**Date**: February 2026  
**Project**: MSPR - European Night Trains Environmental Impact Analysis