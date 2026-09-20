import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_journal_entry_creates_nutrition_logs(client):
    payload = {
        "date": "2026-09-20",
        "raw_text": "Had a protein shake and banana for a post-workout recovery breakfast. Later ate grilled salmon with rice."
    }
    resp = client.post("/api/journal", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nutrition"]["total_calories"] > 0

    # Query /api/journal/nutrition/2026-09-20
    nut_resp = client.get("/api/journal/nutrition/2026-09-20")
    assert nut_resp.status_code == 200
    logs = nut_resp.json()
    assert len(logs) >= 2
    item_names = [l["item_name"].lower() for l in logs]
    assert any("shake" in n for n in item_names) or any("banana" in n for n in item_names) or any("salmon" in n for n in item_names)
    assert any(l["estimated_calories"] > 0 for l in logs)
    assert any(l["protein"] > 0 for l in logs)
