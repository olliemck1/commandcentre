"""Scheduler Service for Command Centre.

Configured with:
- Persistent SQLite jobstore (SQLAlchemyJobStore) so jobs persist across container restarts.
- Europe/London timezone everywhere (DST-safe).
- Idempotent job registration with static IDs and misfire_grace_time=900 (15 mins).
- Schedule:
  - 07:35: Garmin morning sync
  - 07:45: Morning briefing (sleep score, resting HR, lecture schedule/rooms, deadlines)
  - 21:30: Journal nudge with 1-5 mood buttons (skips if already logged today)
  - 23:55: Nightly rollup (upserts DailySummary, updates UserContext)
  - Every 2 minutes: Reminder queue check (dispatches pending reminders due now)
- Resilient Telegram messaging with retry on NetworkError / RetryAfter.
"""
import logging
import asyncio
from zoneinfo import ZoneInfo
from datetime import datetime, date, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import settings
from ..database import SessionLocal
from .garmin_service import garmin_service
from .rollup_service import rollup_service
from ..models.journal import JournalEntry
from ..models.reminder import Reminder
from ..models.daily_metrics import DailyMetrics
from ..models.university import TimetableEvent, Deadline

logger = logging.getLogger("scheduler_service")
LONDON_TZ = ZoneInfo("Europe/London")

def get_london_now() -> datetime:
    """Returns current datetime in Europe/London timezone."""
    return datetime.now(LONDON_TZ)

def get_london_today_str() -> str:
    """Returns current date string (YYYY-MM-DD) in Europe/London timezone."""
    return get_london_now().strftime("%Y-%m-%d")

async def send_telegram_notification(
    text: str,
    reply_markup=None,
    parse_mode: Optional[str] = "Markdown"
) -> bool:
    """Resilient Telegram notification sender for background scheduler jobs.
    Handles network timeouts and RetryAfter without crashing scheduler worker threads."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.ALLOWED_TELEGRAM_USER_ID
    if not token or not chat_id:
        logger.info(f"Telegram notification skipped (no token or allowed user ID). Message preview: {text[:80]}")
        return False

    # Extract first chat ID if comma-separated
    target_chat_id = chat_id.split(",")[0].strip()

    try:
        from telegram import Bot
        from telegram.error import RetryAfter, TimedOut, NetworkError
        bot = Bot(token=token)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                await bot.send_message(
                    chat_id=target_chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                logger.info(f"Telegram notification successfully dispatched to {target_chat_id}")
                return True
            except RetryAfter as e:
                logger.warning(f"Telegram rate limited (RetryAfter {e.retry_after}s). Waiting...")
                await asyncio.sleep(min(e.retry_after, 10))
            except (TimedOut, NetworkError) as e:
                logger.warning(f"Telegram network issue (attempt {attempt+1}/{max_retries}): {e}")
                await asyncio.sleep(2)
            except Exception as e:
                # If Markdown parsing failed, retry as plain text
                if parse_mode:
                    try:
                        await bot.send_message(
                            chat_id=target_chat_id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=None
                        )
                        return True
                    except Exception as fallback_err:
                        logger.error(f"Telegram send failed even without parse_mode: {fallback_err}")
                logger.error(f"Failed to dispatch Telegram message: {e}")
                return False
    except Exception as e:
        logger.error(f"Error initializing Telegram bot sender: {e}")
        return False
    return False


def _run_async_safely(coro):
    """Executes an async coroutine whether or not an event loop is already active."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # In an active loop, schedule as task
        return asyncio.ensure_future(coro)
    else:
        return asyncio.run(coro)

# Module-level standalone job functions for clean serialization in SQLAlchemyJobStore

def job_garmin_morning_sync():
    """07:35 Morning sync of yesterday and today's telemetry."""
    logger.info("Executing scheduled Garmin morning sync...")
    with SessionLocal() as db:
        try:
            today_str = get_london_today_str()
            yesterday_str = (get_london_now() - timedelta(days=1)).strftime("%Y-%m-%d")
            garmin_service.sync_date(db, yesterday_str)
            garmin_service.sync_date(db, today_str)
            logger.info(f"Garmin morning sync complete for {yesterday_str} and {today_str}")
        except Exception as e:
            logger.error(f"Garmin morning sync failed: {e}")

def job_morning_briefing():
    """07:45 Morning briefing: telemetry recovery, lectures/rooms, and deadlines."""
    logger.info("Executing scheduled morning briefing...")
    with SessionLocal() as db:
        try:
            today_str = get_london_today_str()
            yesterday_str = (get_london_now() - timedelta(days=1)).strftime("%Y-%m-%d")

            metric = db.query(DailyMetrics).filter(DailyMetrics.date.in_([yesterday_str, today_str])).order_by(DailyMetrics.date.desc()).first()
            if metric:
                sh = metric.sleep_seconds // 3600
                sm = (metric.sleep_seconds % 3600) // 60
                health_section = (
                    f"🛌 *Sleep & Recovery:*\n"
                    f"• Sleep: *{sh}h {sm}m* (Score: *{metric.sleep_score or 'N/A'}*)\n"
                    f"• Resting HR: *{metric.resting_heart_rate or 'N/A'} bpm*\n"
                )
            else:
                health_section = "🛌 *Sleep & Recovery:* No sleep data recorded yet.\n"

            events = db.query(TimetableEvent).filter(TimetableEvent.start_time.startswith(today_str)).order_by(TimetableEvent.start_time.asc()).all()
            if events:
                tt_lines = []
                for ev in events:
                    loc = ev.location or ev.subject or "Campus"
                    time_str = ev.start_time[11:16] if len(ev.start_time) >= 16 else ""
                    tt_lines.append(f"• *{time_str}* — {ev.title} @ *{loc}*")
                schedule_section = "📅 *Today's Schedule:*\n" + "\n".join(tt_lines) + "\n"
            else:
                schedule_section = "📅 *Today's Schedule:* No lectures or classes scheduled today.\n"

            in_7_days = (get_london_now() + timedelta(days=7)).strftime("%Y-%m-%d")
            deadlines = db.query(Deadline).filter(
                Deadline.due_date >= today_str,
                Deadline.due_date <= in_7_days,
                Deadline.status != "graded"
            ).order_by(Deadline.due_date.asc()).all()

            if deadlines:
                dl_lines = [f"• *{d.title}* ({d.module.code if d.module else 'Uni'}) — Due *{d.due_date}* (Weight: *{d.weight_percentage}%*)" for d in deadlines]
                deadline_section = "🎓 *Impending Deadlines (7 Days):*\n" + "\n".join(dl_lines)
            else:
                deadline_section = "🎓 *Academic Deliverables:* No deadlines due in the next 7 days."

            briefing_text = (
                f"🌅 *Command Centre Morning Briefing* (`{today_str}`)\n\n"
                f"{health_section}\n"
                f"{schedule_section}\n"
                f"{deadline_section}\n\n"
                f"_Have a productive day!_"
            )

            _run_async_safely(send_telegram_notification(briefing_text))
        except Exception as e:
            logger.error(f"Morning briefing failed: {e}")

def job_journal_nudge():
    """21:30 Journal nudge with 1-5 mood buttons.
    Skips if user has already logged a journal entry today."""
    logger.info("Executing scheduled evening journal nudge check...")
    with SessionLocal() as db:
        try:
            today_str = get_london_today_str()

            existing_entry = db.query(JournalEntry).filter(JournalEntry.date == today_str).first()
            if existing_entry:
                logger.info(f"Journal entry already exists for {today_str}. Skipping 21:30 nudge.")
                return

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton("1 😫 Exhausted", callback_data=f"mood:1:{today_str}"),
                    InlineKeyboardButton("2 🥱 Low", callback_data=f"mood:2:{today_str}"),
                ],
                [
                    InlineKeyboardButton("3 😐 Neutral", callback_data=f"mood:3:{today_str}"),
                    InlineKeyboardButton("4 😊 Good", callback_data=f"mood:4:{today_str}"),
                    InlineKeyboardButton("5 🚀 Peak", callback_data=f"mood:5:{today_str}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            nudge_text = (
                f"🌙 *Evening Reflection Nudge* (`{today_str}`)\n\n"
                f"How was your day? Tap a mood rating below, or reply with a quick text or voice note about what you did today."
            )

            _run_async_safely(send_telegram_notification(nudge_text, reply_markup=reply_markup))
        except Exception as e:
            logger.error(f"Journal nudge check failed: {e}")

def job_nightly_rollup():
    """23:55 Nightly rollup."""
    logger.info("Executing scheduled nightly rollup...")
    with SessionLocal() as db:
        try:
            today_str = get_london_today_str()
            _run_async_safely(rollup_service.generate_nightly_rollup(db, today_str))
            logger.info(f"Scheduled nightly rollup finished for {today_str}")
        except Exception as e:
            logger.error(f"Nightly rollup job failed: {e}")

def job_check_reminders():
    """Checks for pending reminders due now and dispatches them."""
    with SessionLocal() as db:
        try:
            now_iso = get_london_now().strftime("%Y-%m-%dT%H:%M:%S")
            pending = db.query(Reminder).filter(
                Reminder.status == "pending",
                Reminder.due_at <= now_iso
            ).all()

            for rem in pending:
                msg = f"⏰ *Reminder:* {rem.title}"
                if rem.notes:
                    msg += f"\n_{rem.notes}_"
                _run_async_safely(send_telegram_notification(msg))
                rem.status = "sent"
                rem.sent_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Reminder dispatcher check failed: {e}")


class SchedulerService:
    def __init__(self, jobstore_url: Optional[str] = None):
        url = jobstore_url or settings.DATABASE_URL
        jobstores = {
            "default": SQLAlchemyJobStore(url=url)
        }
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            timezone=LONDON_TZ
        )

    def start(self):
        if not settings.SYNC_ENABLED:
            logger.info("Scheduler service is disabled via config (SYNC_ENABLED=False)")
            return

        # 1. 07:35 Garmin Sync Job
        self.scheduler.add_job(
            job_garmin_morning_sync,
            trigger=CronTrigger(hour=7, minute=35, timezone=LONDON_TZ),
            id="garmin_morning_sync",
            name="Daily Morning Garmin Sync (07:35)",
            replace_existing=True,
            misfire_grace_time=900
        )

        # 2. 07:45 Morning Briefing Job
        self.scheduler.add_job(
            job_morning_briefing,
            trigger=CronTrigger(hour=7, minute=45, timezone=LONDON_TZ),
            id="morning_briefing",
            name="Daily Morning Briefing (07:45)",
            replace_existing=True,
            misfire_grace_time=900
        )

        # 3. 21:30 Journal Nudge Job (with 1-5 mood buttons)
        self.scheduler.add_job(
            job_journal_nudge,
            trigger=CronTrigger(hour=21, minute=30, timezone=LONDON_TZ),
            id="journal_nudge",
            name="Daily Evening Journal Nudge (21:30)",
            replace_existing=True,
            misfire_grace_time=900
        )

        # 4. 23:55 Nightly Rollup Job
        self.scheduler.add_job(
            job_nightly_rollup,
            trigger=CronTrigger(hour=23, minute=55, timezone=LONDON_TZ),
            id="nightly_rollup",
            name="Daily Nightly Rollup (23:55)",
            replace_existing=True,
            misfire_grace_time=900
        )

        # 5. Persistent Reminders Check (Every 2 minutes)
        self.scheduler.add_job(
            job_check_reminders,
            trigger=IntervalTrigger(minutes=2, timezone=LONDON_TZ),
            id="check_reminders",
            name="Periodic Reminder Queue Dispatcher",
            replace_existing=True,
            misfire_grace_time=300
        )

        try:
            if not self.scheduler.running:
                self.scheduler.start()
            logger.info("Scheduler service started with persistent jobstore in Europe/London timezone.")
        except Exception as e:
            logger.error(f"Failed to start scheduler service: {e}")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler successfully shut down")


scheduler_service = SchedulerService()
