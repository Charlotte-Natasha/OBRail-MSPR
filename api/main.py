from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, database
from typing import List

app = FastAPI(title="ObRail Europe Rail API")

# Dependency to get a database session per request
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Health Check Endpoint
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")

# 2. Get All Routes
@app.get("/routes", response_model=List[models.RouteSchema])
def read_routes(db: Session = Depends(get_db)):
    return db.query(models.Route).all()

# 3. Filter Routes by Origin City
@app.get("/routes/{origin}", response_model=List[models.RouteSchema])
def read_routes_by_origin(origin: str, db: Session = Depends(get_db)):
    routes = db.query(models.Route).filter(models.Route.origin_name == origin).all()
    if not routes:
        raise HTTPException(status_code=404, detail=f"No routes found from {origin}")
    return routes

# 4. Comparative CO2 Analysis Endpoint
@app.get("/comparison/{route_id}")
def get_co2_comparison(route_id: int, db: Session = Depends(get_db)):
    route = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return {
        "route": route.route_name,
        "train_kg_co2": route.train_co2_kg,
        "plane_kg_co2": route.plane_co2_kg,
        "savings_kg": route.co2_savings_kg,
        "source": route.emission_source
    }