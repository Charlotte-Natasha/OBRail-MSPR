"""
ObRail Europe - Countries API Tests
=====================================
Tests for all /api/countries endpoints.
"""

import pytest
import httpx
from conftest import BASE_URL


def test_get_all_countries():
    """GET /api/countries returns valid response structure"""
    response = httpx.get(f"{BASE_URL}/api/countries")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "countries" in data
    assert isinstance(data["countries"], list)


def test_get_countries_response_fields():
    """GET /api/countries returns expected fields per country"""
    response = httpx.get(f"{BASE_URL}/api/countries")
    data = response.json()
    if data["total"] == 0:
        pytest.skip("No data in database")
    country = data["countries"][0]
    expected_fields = [
        "country_code", "country_name", "route_count",
        "total_co2_savings_kg", "avg_distance_km"
    ]
    for field in expected_fields:
        assert field in country, f"Missing field: {field}"


def test_get_country_routes_valid():
    """GET /api/countries/FR returns 200 or 404 depending on data"""
    response = httpx.get(f"{BASE_URL}/api/countries/FR")
    assert response.status_code in [200, 404]


def test_get_country_routes_structure():
    """GET /api/countries/FR returns correct structure when data exists"""
    response = httpx.get(f"{BASE_URL}/api/countries/FR")
    if response.status_code == 404:
        pytest.skip("No French routes in database")
    data = response.json()
    assert "country_code" in data
    assert "total_routes" in data
    assert "routes" in data
    assert data["country_code"] == "FR"


def test_get_country_not_found():
    """GET /api/countries/XX returns 404 for unknown country"""
    response = httpx.get(f"{BASE_URL}/api/countries/XX")
    assert response.status_code == 404


def test_get_country_invalid_code():
    """GET /api/countries/INVALID returns 404"""
    response = httpx.get(f"{BASE_URL}/api/countries/INVALID")
    assert response.status_code == 404