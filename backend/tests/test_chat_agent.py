import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_chat_assistant_university_and_nutrition_query(client):
    # Log a test journal with nutrition
    client.post("/api/journal", json={
        "date": "2026-09-20",
        "raw_text": "Ate a healthy chicken bowl with brown rice (600 cal). Also studied COMP2181."
    })

    # Composite query: "What assignments are due this week and how many calories did I eat yesterday?"
    req = {
        "message": "What classes or assignments do I have coming up, and what did I eat recently?"
    }
    resp = client.post("/api/chat", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 20
    assert "citations" in data
    assert len(data["citations"]) > 0

def test_chat_assistant_person_query(client):
    # Log a journal mentioning Alex to establish the test entity
    client.post("/api/journal", json={
        "date": "2026-09-20",
        "raw_text": "Met Alex Vance today. He started a new role as Senior Systems Engineer at TechCorp."
    })

    # Person query: "When was the last time I saw Alex and what was his new job?"
    req = {
        "message": "When was the last time I saw Alex and what was his new job?"
    }
    resp = client.post("/api/chat", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert "Alex" in data["answer"]
    # Check citations for person or interaction
    citation_types = [c["type"] for c in data["citations"]]
    assert "person" in citation_types or "interaction" in citation_types

def test_chat_stream_endpoint(client):
    req = {
        "message": "Summarize my steps and sleep for today."
    }
    resp = client.post("/api/chat/stream", json=req)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "event: delta" in text or "event: done" in text
