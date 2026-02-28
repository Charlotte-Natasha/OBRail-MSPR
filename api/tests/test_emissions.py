"""
ObRail Europe - Emissions API Tests
=====================================
Tests for all /api/emissions endpoints.
"""

import pytest
import httpx
from conftest import BASE_URL


def test_get_emissions_summary():
    """GET /api/emissions/summary returns valid structure"""
    response = httpx.get(f"{BASE_URL}/api/emissions/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_routes" in data
    assert "total_co2_saved_kg" in data
    assert "total_co2_saved_tons" in data
    assert "countries_covered" in data
    assert "average_savings_per_route_kg" in data
    assert "average_savings_percent" in data


def test_emissions_summary_values_are_non_negative():
    """Emissions summary values should be zero or positive"""
    response = httpx.get(f"{BASE_URL}/api/emissions/summary")
    data = response.json()
    assert data["total_routes"] >= 0
    assert (data["total_co2_saved_kg"] or 0) >= 0
    assert data["countries_covered"] >= 0


def test_get_top_routes():
    """GET /api/emissions/top-routes returns valid structure"""
    response = httpx.get(f"{BASE_URL}/api/emissions/top-routes")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "routes" in data
    assert isinstance(data["routes"], list)


def test_get_top_routes_default_limit():
    """GET /api/emissions/top-routes default returns at most 20 routes"""
    response = httpx.get(f"{BASE_URL}/api/emissions/top-routes")
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) <= 20


def test_get_top_routes_with_limit():
    """GET /api/emissions/top-routes?limit=5 returns at most 5"""
    response = httpx.get(f"{BASE_URL}/api/emissions/top-routes?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) <= 5


def test_top_routes_ordered_by_savings():
    """Top routes should be ordered by co2_savings_kg descending"""
    response = httpx.get(f"{BASE_URL}/api/emissions/top-routes?limit=10")
    data = response.json()
    if len(data["routes"]) < 2:
        pytest.skip("Not enough routes to test ordering")
    savings = [r["co2_savings_kg"] for r in data["routes"] if r["co2_savings_kg"]]
    assert savings == sorted(savings, reverse=True)


def test_top_routes_response_fields():
    """Top routes contain expected fields"""
    response = httpx.get(f"{BASE_URL}/api/emissions/top-routes?limit=1")
    data = response.json()
    if data["total"] == 0:
        pytest.skip("No routes in database")
    route = data["routes"][0]
    expected_fields = [
        "route_name", "origin_country", "destination_country",
        "distance_km", "co2_savings_kg"
    ]
    for field in expected_fields:
        assert field in route, f"Missing field: {field}"