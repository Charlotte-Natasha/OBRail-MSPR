"""
Data Models
===========

Pydantic models for API request/response validation.
These define what data looks like and FastAPI uses them
for automatic validation and documentation.

Author: ObRail Europe
"""

from pydantic import BaseModel
from typing import Optional
from datetime import date

# ============================================
# ROUTE MODELS
# ============================================

class RouteBase(BaseModel):
    """Base route model with all fields"""
    route_id: int
    route_name: Optional[str]
    route_name_simple: Optional[str]
    origin: str
    destination: str
    origin_country: Optional[str]
    destination_country: Optional[str]
    distance_km: Optional[float]
    service_type: Optional[str]
    train_type: Optional[str]
    train_gco2_pkm: Optional[float]
    plane_gco2_pkm: Optional[float]
    train_co2_kg: Optional[float]
    plane_co2_kg: Optional[float]
    co2_savings_kg: Optional[float]
    savings_percent: Optional[float]
    emission_source: Optional[str]
    calculation_date: Optional[date]

    class Config:
        from_attributes = True  # Allows SQLAlchemy models to work


class RouteSummary(BaseModel):
    """Simplified route for lists"""
    route_id: int
    route_name_simple: str
    origin: str
    destination: str
    origin_country: str
    destination_country: str
    distance_km: float
    co2_savings_kg: float
    
    class Config:
        from_attributes = True


# ============================================
# COUNTRY MODELS
# ============================================

class Country(BaseModel):
    """Country with statistics"""
    country_code: str
    country_name: Optional[str]
    route_count: int
    total_co2_savings_kg: float
    total_co2_savings_tons: float
    avg_distance_km: float

    class Config:
        from_attributes = True


# ============================================
# SUMMARY MODELS
# ============================================

class EmissionsSummary(BaseModel):
    """Overall CO2 statistics"""
    total_routes: int
    total_co2_saved_kg: float
    total_co2_saved_tons: float
    average_savings_per_route_kg: float
    average_savings_percent: float
    countries_covered: int

    class Config:
        from_attributes = True


# ============================================
# RESPONSE MODELS
# ============================================

class RoutesResponse(BaseModel):
    """Response for /routes endpoint"""
    total: int
    routes: list[RouteSummary]


class CountriesResponse(BaseModel):
    """Response for /countries endpoint"""
    total: int
    countries: list[Country]