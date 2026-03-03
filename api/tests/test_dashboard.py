"""
ObRail Europe - Dashboard Page Tests
======================================
Tests that all HTML dashboard pages load correctly.
"""

import httpx
from conftest import BASE_URL


def test_dashboard_loads():
    """Main dashboard returns 200 and contains ObRail branding"""
    response = httpx.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ObRail" in response.text


def test_dashboard_contains_kpi_cards():
    """Dashboard contains the expected KPI sections"""
    response = httpx.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert "Lignes totales" in response.text  
    assert "CO" in response.text  # CO2 section


def test_routes_page_loads():
    """Routes browsing page returns 200 HTML"""
    response = httpx.get(f"{BASE_URL}/routes-page")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_routes_page_filter_by_country():
    """Routes page with country filter returns 200"""
    response = httpx.get(f"{BASE_URL}/routes-page?country=FR")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_routes_page_filter_by_type():
    """Routes page with train type filter returns 200"""
    response = httpx.get(f"{BASE_URL}/routes-page?train_type=night")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_countries_page_loads():
    """Countries overview page returns 200 HTML"""
    response = httpx.get(f"{BASE_URL}/countries-page")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]