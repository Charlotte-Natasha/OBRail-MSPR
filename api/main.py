"""
ObRail Europe - FastAPI Application
====================================

Main API application with REST endpoints and dashboard.

Provides:
- REST API endpoints (JSON responses)
- Dashboard web pages (HTML templates)
- Automatic API documentation

Author: ObRail Europe
Version: 1.0
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import os

# Import local modules
from database import get_db
from models import (
    RouteBase, RouteSummary, RoutesResponse,
    Country, CountriesResponse,
    EmissionsSummary
)

# ============================================
# FASTAPI APP SETUP
# ============================================

app = FastAPI(
    title="ObRail Europe API",
    description="API for European night train routes with environmental impact data",
    version="1.0.0",
    docs_url="/api/docs",  # Swagger UI documentation
    redoc_url="/api/redoc"  # ReDoc documentation
)

# Mounts static files (CSS, JS, images)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates for HTML pages
templates = Jinja2Templates(directory="templates")

# ============================================
# DASHBOARD ROUTES (HTML Pages)
# ============================================

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, db: Session = Depends(get_db)):
    """
    Main dashboard page
    Shows overview statistics and charts
    """
    
    # Get summary statistics
    summary_query = text("""
    SELECT 
        COUNT(*) as total_routes,
        COUNT(*) FILTER (WHERE train_type = 'day') as day_routes,
        COUNT(*) FILTER (WHERE train_type = 'night') as night_routes,
        COUNT(DISTINCT origin_country) as countries,
        ROUND(SUM(co2_savings_kg)::numeric, 2) as total_savings_kg,
        COUNT(*) FILTER (WHERE distance_km <= 1600) as viable_alternatives
        FROM fact_routes
        """)

    result = db.execute(summary_query).fetchone()

    summary = {
        "total_routes": result[0],
        "day_routes": result[1],
        "night_routes": result[2],
        "countries": result[3],
        "total_co2_saved_kg": result[4],
        "total_co2_saved_tons": round(result[4] / 1000, 2) if result[4] else 0,
        "viable_alternatives": result[5]
    }
    
    # Get top 10 routes by savings
    top_routes_query = text("""
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
    """)
    
    top_routes = db.execute(top_routes_query).fetchall()
    
    # Get savings by country
    countries_query = text("""
        SELECT 
            origin_country,
            COUNT(*) as route_count,
            ROUND(SUM(co2_savings_kg)::numeric, 2) as total_savings
        FROM fact_routes
        WHERE origin_country IS NOT NULL
        GROUP BY origin_country
        ORDER BY total_savings DESC
        LIMIT 10
    """)
    
    countries = db.execute(countries_query).fetchall()
    
    return templates.TemplateResponse(
        "Dashboard.html",
        {
            "request": request,
            "summary": summary,
            "top_routes": top_routes,
            "countries": countries
        }
    )


@app.get("/routes-page", response_class=HTMLResponse)
async def routes_page(
    request: Request,
    country: Optional[str] = None,
    train_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Routes browsing page with filters
    """
    
    # Build query with optional filters
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
    
    # Get unique countries for filter dropdown
    countries = db.execute(text("""
        SELECT DISTINCT origin_country 
        FROM fact_routes 
        WHERE origin_country IS NOT NULL 
        ORDER BY origin_country
    """)).fetchall()
    
    return templates.TemplateResponse(
        "Routes.html",
        {
            "request": request,
            "routes": routes,
            "countries": [c[0] for c in countries],
            "selected_country": country,
            "selected_type": train_type
        }
    )


@app.get("/countries-page", response_class=HTMLResponse)
async def countries_page(request: Request, db: Session = Depends(get_db)):
    """
    Countries overview page
    """
    
    query = text("""
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
    """)
    
    countries = db.execute(query).fetchall()
    
    return templates.TemplateResponse(
        "Countries.html",
        {
            "request": request,
            "countries": countries
        }
    )


# ============================================
# REST API ENDPOINTS (JSON Responses)
# ============================================

@app.get("/api/routes", response_model=RoutesResponse)
async def get_routes(
    country: Optional[str] = Query(None, description="Filter by origin country code"),
    train_type: Optional[str] = Query(None, description="Filter by train type (night/day)"),
    limit: int = Query(100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Get all routes with optional filters
    
    - **country**: Filter by origin country (e.g., 'FR', 'DE')
    - **train_type**: Filter by type ('night' or 'day')
    - **limit**: Maximum number of results (default 100)
    """
    
    # Build query dynamically based on filters
    query = "SELECT * FROM fact_routes WHERE 1=1"
    params = {}
    
    if country:
        query += " AND origin_country = :country"
        params["country"] = country
    
    if train_type:
        query += " AND train_type = :train_type"
        params["train_type"] = train_type
    
    query += " ORDER BY co2_savings_kg DESC LIMIT :limit"
    params["limit"] = limit
    
    result = db.execute(text(query), params)
    routes = result.fetchall()
    
    # Convert to RouteSummary objects
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
    
    return RoutesResponse(
        total=len(routes_list),
        routes=routes_list
    )


@app.get("/api/routes/{route_id}", response_model=RouteBase)
async def get_route_by_id(route_id: int, db: Session = Depends(get_db)):
    """
    Get specific route by ID
    
    Returns full route details including all CO2 calculations
    """
    
    query = text("SELECT * FROM fact_routes WHERE route_id = :route_id")
    result = db.execute(query, {"route_id": route_id}).fetchone()
    
    if not result:
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
    """
    Get all countries with route statistics
    
    Returns list of countries with:
    - Number of routes
    - Total CO2 savings
    - Average distance
    """
    
    query = text("""
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
    """)
    
    result = db.execute(query).fetchall()
    
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
    
    return CountriesResponse(
        total=len(countries_list),
        countries=countries_list
    )


@app.get("/api/countries/{country_code}")
async def get_country_routes(country_code: str, db: Session = Depends(get_db)):
    """
    Get all routes for a specific country
    
    Returns routes where origin OR destination matches the country code
    """
    
    query = text("""
        SELECT * FROM fact_routes
        WHERE origin_country = :code OR destination_country = :code
        ORDER BY co2_savings_kg DESC
    """)
    
    result = db.execute(query, {"code": country_code}).fetchall()
    
    if not result:
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
    
    return {
        "country_code": country_code,
        "total_routes": len(routes_list),
        "routes": routes_list
    }


@app.get("/api/emissions/summary", response_model=EmissionsSummary)
async def get_emissions_summary(db: Session = Depends(get_db)):
    """
    Get overall CO2 emissions summary
    
    Returns total statistics across all routes
    """
    
    query = text("""
        SELECT 
            COUNT(*) as total_routes,
            COUNT(DISTINCT origin_country) as countries,
            ROUND(SUM(co2_savings_kg)::numeric, 2) as total_savings_kg,
            ROUND(AVG(co2_savings_kg)::numeric, 2) as avg_savings_kg,
            ROUND(AVG(savings_percent)::numeric, 2) as avg_savings_pct
        FROM fact_routes
    """)
    
    result = db.execute(query).fetchone()
    
    return EmissionsSummary(
        total_routes=result[0],
        countries_covered=result[1],
        total_co2_saved_kg=result[2],
        total_co2_saved_tons=round(result[2] / 1000, 2),
        average_savings_per_route_kg=result[3],
        average_savings_percent=result[4]
    )


@app.get("/api/emissions/top-routes")
async def get_top_routes(limit: int = Query(20, description="Number of top routes"), db: Session = Depends(get_db)):
    """
    Get routes with highest CO2 savings
    
    - **limit**: Number of routes to return (default 20)
    """
    
    query = text("""
        SELECT 
            route_id,
            route_name_simple,
            origin,
            destination,
            origin_country,
            destination_country,
            distance_km,
            co2_savings_kg,
            savings_percent
        FROM fact_routes
        ORDER BY co2_savings_kg DESC
        LIMIT :limit
    """)
    
    result = db.execute(query, {"limit": limit}).fetchall()
    
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
    
    return {
        "total": len(top_routes),
        "routes": top_routes
    }


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    Verifies API and database are working
    """
    
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "message": "ObRail API is running"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


# ============================================
# STARTUP MESSAGE
# ============================================

@app.on_event("startup")
async def startup_event():
    """
    Runs when API starts
    """
    print("=" * 70)
    print("🚀 ObRail Europe API Started!")
    print("=" * 70)
    print("")
    print("📊 Dashboard: http://localhost:8000/")
    print("📚 API Docs:  http://localhost:8000/api/docs")
    print("🔍 Routes:    http://localhost:8000/routes-page")
    print("🌍 Countries: http://localhost:8000/countries-page")
    print("")
    print("=" * 70)