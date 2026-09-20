import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date

from ..config import settings
from ..database import SessionLocal
from .garmin_service import garmin_service

logger = logging.getLogger("scheduler_service")

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def start(self):
        if not settings.SYNC_ENABLED:
            logger.info("Automated Garmin sync scheduler is disabled via config")
            return

        trigger = CronTrigger(
            hour=settings.SYNC_HOUR,
            minute=settings.SYNC_MINUTE
        )

        self.scheduler.add_job(
            self._scheduled_sync_job,
            trigger=trigger,
            id="daily_garmin_sync",
            name="Daily Garmin Connect Sync Job",
            replace_existing=True
        )

        try:
            self.scheduler.start()
            logger.info(f"Scheduler started. Daily sync set for {settings.SYNC_HOUR:02d}:{settings.SYNC_MINUTE:02d}")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler successfully shut down")

    def _scheduled_sync_job(self):
        logger.info("Executing scheduled Garmin sync job...")
        db = SessionLocal()
        try:
            today_str = date.today().isoformat()
            garmin_service.sync_date(db, today_str)
            logger.info(f"Scheduled sync complete for {today_str}")
        except Exception as e:
            logger.error(f"Scheduled sync failed: {e}")
        finally:
            db.close()

scheduler_service = SchedulerService()
