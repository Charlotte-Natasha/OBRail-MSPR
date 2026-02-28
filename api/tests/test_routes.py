"""
ObRail Europe - Routes API Tests
==================================
Tests for all /api/routes endpoints.
"""

import pytest
import httpx
from conftest import BASE_URL


def test_get_all_routes():
    """GET /api/routes returns valid response structure"""
    response = httpx.get(f"{BASE_URL}/api/routes")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "routes" in data
    assert isinstance(data["routes"], list)
    assert data["total"] >= 0


def test_get_routes_default_limit():
    """GET /api/routes default limit is 100"""
    response = httpx.get(f"{BASE_URL}/api/routes")
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) <= 100


def test_get_routes_with_limit():
    """GET /api/routes?limit=5 returns at most 5 routes"""
    response = httpx.get(f"{BASE_URL}/api/routes?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) <= 5


def test_get_routes_filter_by_country():
    """GET /api/routes?country=FR returns only French origin routes"""
    response = httpx.get(f"{BASE_URL}/api/routes?country=FR")
    assert response.status_code == 200
    data = response.json()
    for route in data["routes"]:
        assert route["origin_country"] == "FR"


def test_get_routes_filter_by_night_train():
    """GET /api/routes?train_type=night returns only night trains"""
    response = httpx.get(f"{BASE_URL}/api/routes?train_type=night")
    assert response.status_code == 200
    data = response.json()
    for route in data["routes"]:
        assert route.get("train_type") in ["night", None]


def test_get_routes_filter_by_day_train():
    """GET /api/routes?train_type=day returns only day trains"""
    response = httpx.get(f"{BASE_URL}/api/routes?train_type=day")
    assert response.status_code == 200
    data = response.json()
    for route in data["routes"]:
        assert route.get("train_type") in ["day", None]


def test_get_routes_combined_filters():
    """GET /api/routes?country=FR&train_type=night combines filters"""
    response = httpx.get(f"{BASE_URL}/api/routes?country=FR&train_type=night")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["routes"], list)


def test_get_route_by_id(first_route_id):
    """GET /api/routes/{id} returns the correct route"""
    if first_route_id is None:
        pytest.skip("No routes in database")
    response = httpx.get(f"{BASE_URL}/api/routes/{first_route_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["route_id"] == first_route_id


def test_get_route_response_fields(first_route_id):
    """GET /api/routes/{id} returns all expected fields"""
    if first_route_id is None:
        pytest.skip("No routes in database")
    response = httpx.get(f"{BASE_URL}/api/routes/{first_route_id}")
    data = response.json()
    expected_fields = [
        "route_id", "origin", "destination",
        "origin_country", "destination_country",
        "distance_km", "co2_savings_kg"
    ]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"


def test_get_route_not_found():
    """GET /api/routes/999999 returns 404"""
    response = httpx.get(f"{BASE_URL}/api/routes/999999")
    assert response.status_code == 404