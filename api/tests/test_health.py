"""
ObRail Europe - Health Check Tests
====================================
Tests that the API and database are reachable and healthy.
"""

import httpx
from conftest import BASE_URL


def test_health_check():
    """API returns healthy status with database connected"""
    response = httpx.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "message" in data


def test_api_docs_accessible():
    """Swagger UI documentation is accessible"""
    response = httpx.get(f"{BASE_URL}/api/docs")
    assert response.status_code == 200


def test_redoc_accessible():
    """ReDoc documentation is accessible"""
    response = httpx.get(f"{BASE_URL}/api/redoc")
    assert response.status_code == 200