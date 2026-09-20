import uuid
from datetime import datetime, timedelta, date
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.university import Module, TimetableEvent
from app.services.timetable_service import (
    extract_module_info,
    determine_event_type,
    ensure_module,
    timetable_service
)
from app.services.agent_tools import get_university_timetable

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_extract_module_info():
    code, title = extract_module_info("COMP2221: Programming Paradigms - Lecture")
    assert code == "COMP2221"
    assert title == "Programming Paradigms"

    code2, title2 = extract_module_info("MATH2731: Computational Mathematics II - Drop-In Class")
    assert code2 == "MATH2731"
    assert title2 == "Computational Mathematics II"

    code3, title3 = extract_module_info("Review session in room TLC123")
    assert code3 is None

def test_determine_event_type():
    assert determine_event_type("Programming Paradigms - Lecture") == "lecture"
    assert determine_event_type("Math Drop-In Class") == "drop-in"
    assert determine_event_type("AI Lab Practical") == "practical"
    assert determine_event_type("Office Hours - Sam Fearn") == "office-hours"
    assert determine_event_type("Coursework 2 Submission Deadline") == "deadline"

def test_ensure_module():
    db = SessionLocal()
    unique_code = f"CMP{uuid.uuid4().hex[:4].upper()}"
    try:
        mod = ensure_module(db, unique_code, "Advanced Quantum Computing")
        assert mod.id is not None
        assert mod.code == unique_code
        assert mod.title == "Advanced Quantum Computing"

        # Calling again returns same module without duplicates
        mod2 = ensure_module(db, unique_code)
        assert mod2.id == mod.id
    finally:
        db.close()

def test_manual_timetable_crud_and_status(client):
    unique_mod = f"TST{uuid.uuid4().hex[:4].upper()}"
    now_str = datetime.utcnow().isoformat()
    end_str = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    
    # 1. Create manual event
    res = client.post("/api/timetable", json={
        "title": f"{unique_mod}: Special Seminar",
        "start_time": now_str,
        "end_time": end_str,
        "location": "TLC123",
        "module_code": unique_mod,
        "event_type": "seminar"
    })
    assert res.status_code == 200, res.text
    created = res.json()
    assert created["title"] == f"{unique_mod}: Special Seminar"
    assert created["module_code"] == unique_mod
    assert created["location"] == "TLC123"
    event_id = created["id"]

    # 2. Get timetable list
    res_list = client.get(f"/api/timetable?module_code={unique_mod}")
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    assert any(it["id"] == event_id for it in items)

    # 3. Check status
    res_status = client.get("/api/timetable/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["total_events"] >= 1

    # 4. Delete event
    res_del = client.delete(f"/api/timetable/{event_id}")
    assert res_del.status_code == 200
    assert res_del.json()["message"] == "Timetable event deleted"

def test_agent_tool_get_university_timetable():
    db = SessionLocal()
    unique_code = f"MTH{uuid.uuid4().hex[:4].upper()}"
    unique_sync = f"test_agent_{uuid.uuid4().hex[:8]}"
    try:
        # Insert a sample event
        today_iso = date.today().isoformat() + "T10:00:00"
        ev = TimetableEvent(
            sync_id=unique_sync,
            source="test",
            title=f"{unique_code}: Statistical Inference II - Lecture",
            location="ER201",
            subject="ER201",
            start_time=today_iso,
            end_time=date.today().isoformat() + "T12:00:00",
            event_type="lecture",
            module_code=unique_code,
            status="scheduled"
        )
        db.add(ev)
        db.commit()

        # Query tool
        result = get_university_timetable(db, module_code=unique_code)
        assert result["count"] >= 1
        assert len(result["citations"]) >= 1
        assert "Statistical Inference" in result["citations"][0]["title"]
        assert "ER201" in result["citations"][0]["snippet"]
    finally:
        db.close()
