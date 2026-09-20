import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_garmin_status_endpoint(client):
    response = client.get("/api/garmin/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "mode" in data

def test_get_and_sync_metrics(client):
    # Fetch metrics for a date
    response = client.get("/api/metrics/2026-09-20")
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-09-20"
    assert "steps" in data
    assert "total_calories_burned" in data

def test_post_journal_and_crm_integration(client):
    payload = {
        "date": "2026-09-20",
        "raw_text": "Lunch with Marcus Vance at Dishoom. Marcus started a new job in fintech. Ate chicken and rice (around 650 cal)."
    }
    response = client.post("/api/journal", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-09-20"
    assert data["nutrition"]["total_calories"] > 0
    assert len(data["people"]) >= 1

    # Verify CRM has Marcus
    people_resp = client.get("/api/people?search=Marcus")
    assert people_resp.status_code == 200
    people = people_resp.json()
    assert any("Marcus" in p["name"] for p in people)

def test_seed_demo_data(client):
    response = client.post("/api/seed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "message" in data
