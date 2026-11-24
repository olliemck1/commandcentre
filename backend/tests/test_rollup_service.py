import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.daily_summary import DailySummary
from app.models.user_context import UserContext
from app.models.daily_metrics import DailyMetrics
from app.models.journal import JournalEntry
from app.services.rollup_service import rollup_service

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.mark.anyio
async def test_idempotent_rollup_upsert(test_db):
    target_date = "2026-10-15"

    # Add Garmin metric
    test_db.add(DailyMetrics(
        date=target_date,
        steps=11000,
        step_goal=10000,
        total_calories_burned=2400,
        active_calories=500,
        sleep_seconds=28800,
        sleep_score=85
    ))
    test_db.add(JournalEntry(
        date=target_date,
        raw_text="Focused study day working on COMP2181 kernel driver. Had oat milk flat whites.",
        summary="Focused OS study day.",
        mood="Focused",
        tags_json=json.dumps(["study", "kernel"])
    ))
    test_db.commit()

    # First rollup run
    summary1 = await rollup_service.generate_nightly_rollup(test_db, target_date)
    assert summary1 is not None
    assert summary1.date == target_date
    assert summary1.id is not None
    s1_id = summary1.id

    # Verify source_record_ids
    sources = json.loads(summary1.source_record_ids_json)
    assert any("garmin:" in s for s in sources)
    assert any("journal:" in s for s in sources)

    # Re-run same rollup (e.g. late sync or retry)
    summary2 = await rollup_service.generate_nightly_rollup(test_db, target_date)
    assert summary2.id == s1_id  # Exactly the same row updated, not duplicated
    assert test_db.query(DailySummary).filter(DailySummary.date == target_date).count() == 1

@pytest.mark.anyio
async def test_bounded_append_safe_user_context(test_db):
    target_date = "2026-10-15"

    # Pre-seed UserContext with initial preference
    initial_pref = UserContext(
        key="preferences",
        content=json.dumps(["Early riser", "Prefers dark mode UI"]),
        version=1
    )
    test_db.add(initial_pref)
    test_db.commit()

    # Rollup input with new fact
    test_db.add(JournalEntry(
        date=target_date,
        raw_text="Met friends and ordered an oat milk flat white. Working on COMP2181 kernel driver.",
        mood="Content"
    ))
    test_db.commit()

    await rollup_service.generate_nightly_rollup(test_db, target_date)

    updated_pref = test_db.query(UserContext).filter(UserContext.key == "preferences").first()
    assert updated_pref is not None
    assert updated_pref.version >= 2
    facts = json.loads(updated_pref.content)
    # Existing facts preserved
    assert "Early riser" in facts
    assert "Prefers dark mode UI" in facts
    # New fact appended
    assert any("flat white" in f.lower() or "oat milk" in f.lower() for f in facts)
