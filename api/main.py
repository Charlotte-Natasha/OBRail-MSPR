"""
ObRail Europe - FastAPI Application
====================================
Main API application with REST endpoints and dashboard.

Author: ObRail Europe
Version: 1.0
"""

import csv
import io
import logging
import os
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from models import (
    RouteBase, RouteSummary, RoutesResponse,
    Country, CountriesResponse,
    EmissionsSummary
)

# ============================================
# LOGGING SETUP
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("obrail")

# ============================================
# FASTAPI APP SETUP
# ============================================

app = FastAPI(
    title="ObRail Europe API",
    description="API for European night train routes with environmental impact data",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# ============================================
# HELPER - DATA QUALITY QUERY
# ============================================

def get_data_quality(db: Session) -> dict:
    """Runs data quality checks and returns results as a dict"""
    result = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE origin IS NULL) as null_origins,
            COUNT(*) FILTER (WHERE destination IS NULL) as null_destinations,
            COUNT(*) FILTER (WHERE distance_km IS NULL) as null_distances,
            COUNT(*) FILTER (WHERE co2_savings_kg IS NULL) as null_co2,
            COUNT(*) FILTER (WHERE origin_country IS NULL) as null_countries,
            COUNT(*) FILTER (WHERE co2_savings_kg < 0) as negative_savings,
            COUNT(*) FILTER (WHERE distance_km <= 0) as invalid_distances,
            MAX(calculation_date) as last_load_date
        FROM fact_routes
    """)).fetchone()

    total_issues = (
        result[0] + result[1] + result[2] +
        result[3] + result[4] + result[5] + result[6]
    )

    if total_issues > 0:
        logger.warning(f"Data quality issues detected — {total_issues} total issues found")
    else:
        logger.info("Data quality check passed — no issues found")

    return {
        "null_origins": result[0],
        "null_destinations": result[1],
        "null_distances": result[2],
        "null_co2": result[3],
        "null_countries": result[4],
        "negative_savings": result[5],
        "invalid_distances": result[6],
        "last_load_date": result[7],
        "total_issues": total_issues
    }


# ============================================
# DASHBOARD PAGES (HTML)
# ============================================

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, db: Session = Depends(get_db)):
    """Main dashboard — KPIs, emissions comparison, top routes table"""
    logger.info("Dashboard home page requested")

    result = db.execute(text("""
        SELECT
            COUNT(*) as total_routes,
            COUNT(*) FILTER (WHERE train_type = 'day') as day_routes,
            COUNT(*) FILTER (WHERE train_type = 'night') as night_routes,
            COUNT(DISTINCT origin_country) as countries,
            ROUND(SUM(co2_savings_kg)::numeric, 2) as total_savings_kg,
            COUNT(*) FILTER (WHERE distance_km <= 1600) as viable_alternatives
        FROM fact_routes
    """)).fetchone()

    summary = {
        "total_routes": result[0],
        "day_routes": result[1],
        "night_routes": result[2],
        "countries": result[3],
        "total_co2_saved_kg": result[4],
        "total_co2_saved_tons": round(result[4] / 1000, 2) if result[4] else 0,
        "viable_alternatives": result[5]
    }

    logger.info(f"Dashboard summary — {summary['total_routes']} routes, {summary['countries']} countries, {summary['total_co2_saved_tons']}t CO2 saved")

    top_routes = db.execute(text("""
        SELECT
            route_name_simple,
            origin_country,
            destination_country,
            train_type,
            co2_savings_kg,
            ROUND((distance_km / 200.0)::numeric, 1) as estimated_hours
        FROM v_top_routes_savings
        ORDER BY co2_savings_kg DESC
        LIMIT 10
    """)).fetchall()

    logger.info(f"Top routes loaded — {len(top_routes)} routes")

    return templates.TemplateResponse("Dashboard.html", {
        "request": request,
        "summary": summary,
        "top_routes": top_routes
    })


@app.get("/routes-page", response_class=HTMLResponse)
async def routes_page(
    request: Request,
    country: Optional[str] = None,
    train_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Routes browsing page with filters"""
    logger.info(f"Routes page — country={country}, train_type={train_type}")

    query = "SELECT * FROM fact_routes WHERE 1=1"
    params = {}

    if country:
        query += " AND origin_country = :country"
        params["country"] = country

    if train_type:
        query += " AND train_type = :train_type"
        params["train_type"] = train_type

    query += " ORDER BY co2_savings_kg DESC LIMIT 100"

    routes = db.execute(text(query), params).fetchall()
    logger.info(f"Routes page — {len(routes)} routes returned")

    countries = db.execute(text("""
        SELECT DISTINCT origin_country
        FROM fact_routes
        WHERE origin_country IS NOT NULL
        ORDER BY origin_country
    """)).fetchall()

    return templates.TemplateResponse("Routes.html", {
        "request": request,
        "routes": routes,
        "countries": [c[0] for c in countries],
        "selected_country": country,
        "selected_type": train_type
    })


@app.get("/countries-page", response_class=HTMLResponse)
async def countries_page(request: Request, db: Session = Depends(get_db)):
    """Countries overview page with data quality monitor"""
    logger.info("Countries page requested")

    countries = db.execute(text("""
        SELECT
            origin_country,
            COUNT(*) as route_count,
            ROUND(AVG(distance_km)::numeric, 2) as avg_distance,
            ROUND(SUM(co2_savings_kg)::numeric, 2) as total_savings,
            ROUND(SUM(co2_savings_kg)::numeric / 1000, 2) as total_savings_tons,
            COUNT(*) FILTER (WHERE train_type = 'day') as day_routes,
            COUNT(*) FILTER (WHERE train_type = 'night') as night_routes,
            ROUND(
                COUNT(*) FILTER (WHERE distance_km > 1600)::numeric
                / NULLIF(COUNT(*), 0) * 100
            ) as coverage_gap
        FROM fact_routes
        WHERE origin_country IS NOT NULL
        GROUP BY origin_country
        ORDER BY total_savings DESC
    """)).fetchall()

    logger.info(f"Countries page — {len(countries)} countries returned")

    data_quality = get_data_quality(db)

    return templates.TemplateResponse("Countries.html", {
        "request": request,
        "countries": countries,
        "data_quality": data_quality
    })


# ============================================
# REST API ENDPOINTS
# ============================================

@app.get("/api/routes/export")
async def export_routes(db: Session = Depends(get_db)):
    """Export all routes as a CSV file"""
    logger.info("GET /api/routes/export — CSV export requested")

    routes = db.execute(text("""
        SELECT
            route_name_simple, origin, destination,
            origin_country, destination_country,
            distance_km, train_type,
            co2_savings_kg, savings_percent
        FROM fact_routes
        ORDER BY co2_savings_kg DESC
    """)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Route", "Origin", "Destination",
        "Origin Country", "Destination Country",
        "Distance (km)", "Train Type",
        "CO2 Savings (kg)", "Savings (%)"
    ])
    for r in routes:
        writer.writerow(r)

    output.seek(0)
    logger.info(f"CSV export — {len(routes)} routes exported")

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=obrail_routes.csv"}
    )


@app.get("/api/routes", response_model=RoutesResponse)
async def get_routes(
    country: Optional[str] = Query(None, description="Filter by origin country code (e.g. FR, DE)"),
    train_type: Optional[str] = Query(None, description="Filter by train type (night/day)"),
    origin: Optional[str] = Query(None, description="Filter by departure city (e.g. Paris)"),
    destination: Optional[str] = Query(None, description="Filter by arrival city (e.g. Berlin)"),
    limit: int = Query(100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """Get all routes with optional filters"""
    logger.info(f"GET /api/routes — country={country}, train_type={train_type}, origin={origin}, destination={destination}, limit={limit}")

    query = "SELECT * FROM fact_routes WHERE 1=1"
    params = {}

    if country:
        query += " AND origin_country = :country"
        params["country"] = country

    if train_type:
        query += " AND train_type = :train_type"
        params["train_type"] = train_type

    if origin:
        query += " AND LOWER(origin) LIKE LOWER(:origin)"
        params["origin"] = f"%{origin}%"

    if destination:
        query += " AND LOWER(destination) LIKE LOWER(:destination)"
        params["destination"] = f"%{destination}%"

    query += " ORDER BY co2_savings_kg DESC LIMIT :limit"
    params["limit"] = limit

    routes = db.execute(text(query), params).fetchall()

    routes_list = [
        RouteSummary(
            route_id=r[0],
            route_name_simple=r[2] or "Unknown",
            origin=r[3],
            destination=r[4],
            origin_country=r[5] or "??",
            destination_country=r[6] or "??",
            distance_km=r[7] or 0,
            co2_savings_kg=r[14] or 0
        )
        for r in routes
    ]

    logger.info(f"GET /api/routes — {len(routes_list)} routes returned")
    return RoutesResponse(total=len(routes_list), routes=routes_list)


@app.get("/api/routes/{route_id}", response_model=RouteBase)
async def get_route_by_id(route_id: int, db: Session = Depends(get_db)):
    """Get a specific route by ID"""
    logger.info(f"GET /api/routes/{route_id}")

    result = db.execute(
        text("SELECT * FROM fact_routes WHERE route_id = :route_id"),
        {"route_id": route_id}
    ).fetchone()

    if not result:
        logger.warning(f"Route {route_id} not found")
        raise HTTPException(status_code=404, detail="Route not found")

    return RouteBase(
        route_id=result[0],
        route_name=result[1],
        route_name_simple=result[2],
        origin=result[3],
        destination=result[4],
        origin_country=result[5],
        destination_country=result[6],
        distance_km=result[7],
        service_type=result[8],
        train_type=result[9],
        train_gco2_pkm=result[10],
        plane_gco2_pkm=result[11],
        train_co2_kg=result[12],
        plane_co2_kg=result[13],
        co2_savings_kg=result[14],
        savings_percent=result[15],
        emission_source=result[16],
        calculation_date=result[17]
    )


@app.get("/api/countries", response_model=CountriesResponse)
async def get_countries(db: Session = Depends(get_db)):
    """Get all countries with route statistics"""
    logger.info("GET /api/countries")

    result = db.execute(text("""
        SELECT
            origin_country,
            origin_country as country_name,
            COUNT(*) as route_count,
            ROUND(SUM(co2_savings_kg)::numeric, 2) as total_savings,
            ROUND(AVG(distance_km)::numeric, 2) as avg_distance
        FROM fact_routes
        WHERE origin_country IS NOT NULL
        GROUP BY origin_country
        ORDER BY total_savings DESC
    """)).fetchall()

    countries_list = [
        Country(
            country_code=r[0],
            country_name=r[1],
            route_count=r[2],
            total_co2_savings_kg=r[3],
            total_co2_savings_tons=round(r[3] / 1000, 2),
            avg_distance_km=r[4]
        )
        for r in result
    ]

    logger.info(f"GET /api/countries — {len(countries_list)} countries returned")
    return CountriesResponse(total=len(countries_list), countries=countries_list)


@app.get("/api/countries/{country_code}")
async def get_country_routes(country_code: str, db: Session = Depends(get_db)):
    """Get all routes for a specific country"""
    logger.info(f"GET /api/countries/{country_code}")

    result = db.execute(text("""
        SELECT * FROM fact_routes
        WHERE origin_country = :code OR destination_country = :code
        ORDER BY co2_savings_kg DESC
    """), {"code": country_code}).fetchall()

    if not result:
        logger.warning(f"No routes found for country: {country_code}")
        raise HTTPException(status_code=404, detail="Country not found or no routes")

    routes_list = [
        RouteSummary(
            route_id=r[0],
            route_name_simple=r[2] or "Unknown",
            origin=r[3],
            destination=r[4],
            origin_country=r[5] or "??",
            destination_country=r[6] or "??",
            distance_km=r[7] or 0,
            co2_savings_kg=r[14] or 0
        )
        for r in result
    ]

    logger.info(f"GET /api/countries/{country_code} — {len(routes_list)} routes returned")
    return {
        "country_code": country_code,
        "total_routes": len(routes_list),
        "routes": routes_list
    }


@app.get("/api/emissions/summary", response_model=EmissionsSummary)
async def get_emissions_summary(db: Session = Depends(get_db)):
    """Get overall CO2 emissions summary"""
    logger.info("GET /api/emissions/summary")

    result = db.execute(text("""
        SELECT
            COUNT(*) as total_routes,
            COUNT(DISTINCT origin_country) as countries,
            ROUND(SUM(co2_savings_kg)::numeric, 2) as total_savings_kg,
            ROUND(AVG(co2_savings_kg)::numeric, 2) as avg_savings_kg,
            ROUND(AVG(savings_percent)::numeric, 2) as avg_savings_pct
        FROM fact_routes
    """)).fetchone()

    return EmissionsSummary(
        total_routes=result[0],
        countries_covered=result[1],
        total_co2_saved_kg=result[2],
        total_co2_saved_tons=round(result[2] / 1000, 2) if result[2] else 0,
        average_savings_per_route_kg=result[3],
        average_savings_percent=result[4]
    )


@app.get("/api/emissions/top-routes")
async def get_top_routes(
    limit: int = Query(20, description="Number of top routes"),
    db: Session = Depends(get_db)
):
    """Get routes with highest CO2 savings"""
    logger.info(f"GET /api/emissions/top-routes — limit={limit}")

    result = db.execute(text("""
        SELECT
            route_id, route_name_simple, origin, destination,
            origin_country, destination_country,
            distance_km, co2_savings_kg, savings_percent
        FROM fact_routes
        ORDER BY co2_savings_kg DESC
        LIMIT :limit
    """), {"limit": limit}).fetchall()

    top_routes = [
        {
            "route_id": r[0],
            "route_name": r[1],
            "origin": r[2],
            "destination": r[3],
            "origin_country": r[4],
            "destination_country": r[5],
            "distance_km": r[6],
            "co2_savings_kg": r[7],
            "savings_percent": r[8]
        }
        for r in result
    ]

    logger.info(f"GET /api/emissions/top-routes — {len(top_routes)} routes returned")
    return {"total": len(top_routes), "routes": top_routes}


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check — verifies API and database are working"""
    try:
        db.execute(text("SELECT 1"))
        logger.info("Health check passed")
        return {
            "status": "healthy",
            "database": "connected",
            "message": "ObRail API is running"
        }
    except Exception as e:
        logger.error(f"Health check failed — {str(e)}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


# ============================================
# STARTUP
# ============================================

@app.on_event("startup")
async def startup_event():
    logger.info("ObRail Europe API starting up...")
    print("=" * 70)
    print("🚀 ObRail Europe API Started!")
    print("=" * 70)
    print("📊 Dashboard: http://localhost:8000/")
    print("📚 API Docs:  http://localhost:8000/api/docs")
    print("🔍 Routes:    http://localhost:8000/routes-page")
    print("🌍 Countries: http://localhost:8000/countries-page")
    print("=" * 70)
    logger.info("ObRail Europe API startup complete")