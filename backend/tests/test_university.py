import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

import uuid

def test_create_and_list_modules(client):
    unique_code = f"CMP{uuid.uuid4().hex[:4].upper()}"
    req = {
        "code": unique_code,
        "title": "Quantum Computing & Complexity",
        "term": "Spring 2027",
        "credits": 15,
        "color": "#6366f1",
        "description": "Quantum state superposition and algorithms."
    }
    resp = client.post("/api/modules", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == unique_code
    assert data["title"] == "Quantum Computing & Complexity"

    # List modules
    list_resp = client.get("/api/modules")
    assert list_resp.status_code == 200
    modules = list_resp.json()
    assert any(m["code"] == unique_code for m in modules)

def test_create_update_and_filter_deadlines(client):
    # Get module id
    modules = client.get("/api/modules").json()
    module_id = modules[0]["id"]

    # Create deadline
    d_req = {
        "module_id": module_id,
        "title": "Quantum Teleportation Simulation Lab",
        "due_date": "2026-10-05T23:59:00",
        "weight_percentage": 25.0,
        "status": "pending",
        "priority": "High"
    }
    resp = client.post("/api/deadlines", json=d_req)
    assert resp.status_code == 200
    d_data = resp.json()
    assert d_data["title"] == "Quantum Teleportation Simulation Lab"
    assert d_data["weight_percentage"] == 25.0

    # Update deadline status
    d_id = d_data["id"]
    upd_resp = client.put(f"/api/deadlines/{d_id}", json={"status": "submitted", "grade": 94.0})
    assert upd_resp.status_code == 200
    assert upd_resp.json()["status"] == "submitted"
    assert upd_resp.json()["grade"] == 94.0

def test_create_and_toggle_academic_tasks(client):
    t_req = {
        "title": "Read Nielsen & Chuang Chapter 4",
        "status": "todo",
        "priority": "high"
    }
    resp = client.post("/api/tasks", json=t_req)
    assert resp.status_code == 200
    task = resp.json()
    assert task["status"] == "todo"

    # Toggle to done
    upd_resp = client.put(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert upd_resp.status_code == 200
    assert upd_resp.json()["status"] == "done"
