import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.config import settings
from app.models.journal import JournalEntry
from app.models.reminder import Reminder
from app.models.daily_metrics import DailyMetrics
from app.models.university import TimetableEvent, Deadline
from app.services.scheduler_service import (
    SchedulerService,
    get_london_today_str,
    get_london_now,
    LONDON_TZ
)
from app.services.telegram_bot import handle_callback_query

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_london_timezone_dst_safe():
    now_london = get_london_now()
    assert now_london.tzinfo is not None
    assert str(now_london.tzinfo) == "Europe/London"
    today_str = get_london_today_str()
    assert len(today_str) == 10
    assert today_str.startswith("20")

def test_idempotent_job_registration():
    # Use in-memory SQLite URL for isolated scheduler test
    sched_service = SchedulerService(jobstore_url="sqlite://")
    sched_service.start()
    job_ids = [j.id for j in sched_service.scheduler.get_jobs()]
    assert "garmin_morning_sync" in job_ids
    assert "morning_briefing" in job_ids
    assert "journal_nudge" in job_ids
    assert "nightly_rollup" in job_ids
    assert "check_reminders" in job_ids

    # Check misfire_grace_time
    sync_job = sched_service.scheduler.get_job("garmin_morning_sync")
    assert sync_job.misfire_grace_time == 900

    # Start again (simulating container restart / re-init)
    sched_service.start()
    # Confirm no duplicate job IDs
    assert len([j for j in sched_service.scheduler.get_jobs() if j.id == "garmin_morning_sync"]) == 1
    sched_service.shutdown()

@pytest.mark.anyio
async def test_journal_nudge_skips_if_already_logged(test_db):
    today_str = get_london_today_str()
    test_db.add(JournalEntry(
        date=today_str,
        raw_text="Already journaled this morning.",
        summary="Morning notes"
    ))
    test_db.commit()

    with patch("app.services.scheduler_service.SessionLocal", return_value=test_db):
        with patch("app.services.scheduler_service.send_telegram_notification", new_callable=AsyncMock) as mock_send:
            from app.services.scheduler_service import job_journal_nudge
            job_journal_nudge()
            # Must NOT send notification because entry already exists
            mock_send.assert_not_called()

@pytest.mark.anyio
async def test_journal_nudge_sends_with_mood_keyboard_if_missing(test_db):
    today_str = get_london_today_str()
    # No journal entry present

    with patch("app.services.scheduler_service.SessionLocal", return_value=test_db):
        with patch("app.services.scheduler_service.send_telegram_notification", new_callable=AsyncMock) as mock_send:
            from app.services.scheduler_service import job_journal_nudge
            job_journal_nudge()
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            assert "Evening Reflection Nudge" in args[0]
            assert kwargs.get("reply_markup") is not None

@pytest.mark.anyio
async def test_callback_query_logs_mood(test_db):
    update = MagicMock()
    update.effective_user.id = 123456
    update.callback_query.data = "mood:5:2026-10-15"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    context = MagicMock()

    with patch.object(settings, "ALLOWED_TELEGRAM_USER_ID", "123456"):
        with patch("app.services.telegram_bot.SessionLocal", return_value=test_db):
            await handle_callback_query(update, context)

            update.callback_query.edit_message_text.assert_called_once()
            call_text = update.callback_query.edit_message_text.call_args[0][0]
            assert "Peak (5/5)" in call_text

            entry = test_db.query(JournalEntry).filter(JournalEntry.date == "2026-10-15").first()
            assert entry is not None
            assert entry.mood == "Peak (5/5)"

@pytest.mark.anyio
async def test_reminder_queue_dispatch(test_db):
    past_due = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
    rem = Reminder(
        id=99,
        title="Submit OS Project",
        due_at=past_due,
        status="pending"
    )
    test_db.add(rem)
    test_db.commit()

    with patch("app.services.scheduler_service.SessionLocal", return_value=test_db):
        with patch("app.services.scheduler_service.send_telegram_notification", new_callable=AsyncMock, return_value=True) as mock_send:
            from app.services.scheduler_service import job_check_reminders
            job_check_reminders()

            mock_send.assert_called_once()
            assert "Submit OS Project" in mock_send.call_args[0][0]

            updated_rem = test_db.query(Reminder).filter(Reminder.id == 99).first()
            assert updated_rem.status == "sent"
            assert updated_rem.sent_at is not None
