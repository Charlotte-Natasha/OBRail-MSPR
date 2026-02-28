"""
ObRail Europe - Shared Test Configuration
==========================================
Shared fixtures and config for all test files.

Make sure Docker is running before running tests:
    docker compose up -d
    pytest tests/ -v
"""

import pytest
import httpx

BASE_URL = "http://localhost:8001"


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def first_route_id():
    """Get a valid route ID from the database for use in tests"""
    response = httpx.get(f"{BASE_URL}/api/routes?limit=1")
    data = response.json()
    if data["total"] == 0:
        return None
    return data["routes"][0]["route_id"]