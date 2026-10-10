"""
API smoke tests for HeatPath FastAPI application.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["app_name"] == "HeatPath"


def test_area():
    response = client.get("/api/area")
    assert response.status_code == 200
    data = response.json()
    assert "Pune" in data["name"]
    assert "center" in data
    assert "bbox" in data
    assert "example_pairs" in data
    assert len(data["example_pairs"]) >= 1
    assert "data_sources" in data
    assert "limitations" in data


def test_data_status():
    response = client.get("/api/data-status")
    assert response.status_code == 200
    data = response.json()
    assert "routing" in data
    assert "weather" in data
    assert "solar" in data
    assert "pilot_area" in data


def test_routes_endpoint():
    # Test valid Pune coordinates
    payload = {
        "origin": {"lat": 18.5308, "lon": 73.8475},
        "destination": {"lat": 18.5173, "lon": 73.8415},
        "departure_time": "2026-10-10T14:00:00+05:30",
        "profile": "balanced"
    }
    response = client.post("/api/routes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "routes" in data
    assert len(data["routes"]) >= 1
    # Check that at least one route is recommended
    assert any(r["is_recommended"] for r in data["routes"])
    
    # Check structure of first route
    r0 = data["routes"][0]
    assert "distance_m" in r0
    assert "duration_s" in r0
    assert "avg_exposure_score" in r0
    assert "geometry" in r0
    assert 0.0 <= r0["avg_exposure_score"] <= 1.0
    assert r0["data_source"] in ["live", "cached", "sample"]


def test_routes_identical_origin_destination():
    # Same origin and destination should fail validation (422)
    payload = {
        "origin": {"lat": 18.5308, "lon": 73.8475},
        "destination": {"lat": 18.5308, "lon": 73.8475},
        "departure_time": "2026-10-10T14:00:00+05:30",
        "profile": "balanced"
    }
    response = client.post("/api/routes", json=payload)
    assert response.status_code == 422
