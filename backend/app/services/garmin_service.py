import os
import json
import logging
import random
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from ..config import settings
from ..models.daily_metrics import DailyMetrics

logger = logging.getLogger("garmin_service")

class GarminService:
    def __init__(self):
        self.tokens_dir = Path(settings.GARMIN_TOKENS_DIR)
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self._last_sync_time = None
        self._last_error = None

    def is_configured(self) -> bool:
        return bool(settings.GARMIN_EMAIL and settings.GARMIN_PASSWORD)

    def get_client(self):
        if not self.is_configured():
            return None
        
        try:
            from garminconnect import (
                Garmin,
                GarminConnectAuthenticationError,
                GarminConnectConnectionError,
                GarminConnectTooManyRequestsError
            )
            
            tokenstore = str(self.tokens_dir)
            client = Garmin(
                email=settings.GARMIN_EMAIL,
                password=settings.GARMIN_PASSWORD,
                return_on_mfa=True
            )
            
            # Login with tokenstore support
            client.login(tokenstore=tokenstore)
            
            # Persist tokens
            try:
                client.garth.dump(tokenstore)
            except Exception as dump_err:
                logger.warning(f"Could not dump Garmin tokens: {dump_err}")
                
            self.client = client
            self._last_error = None
            return client
        except Exception as e:
            logger.error(f"Failed to authenticate with Garmin Connect: {e}")
            self._last_error = str(e)
            return None

    def get_status(self) -> Dict[str, Any]:
        configured = self.is_configured()
        has_tokens = any(self.tokens_dir.glob("*.json")) if self.tokens_dir.exists() else False
        
        # Mask email for privacy
        masked_email = None
        if settings.GARMIN_EMAIL:
            parts = settings.GARMIN_EMAIL.split("@")
            if len(parts) == 2:
                name, domain = parts
                masked_name = name[:2] + "***" if len(name) > 2 else "***"
                masked_email = f"{masked_name}@{domain}"
            else:
                masked_email = "***"

        return {
            "connected": self.client is not None,
            "configured": configured,
            "email": masked_email,
            "last_sync": self._last_sync_time.isoformat() if self._last_sync_time else None,
            "session_valid": self.client is not None or has_tokens,
            "mode": "live" if configured else "demo",
            "message": self._last_error or ("Ready (Live mode)" if configured else "Running in Demo / Simulated Mode (Provide credentials in .env to link Garmin)")
        }

    def sync_date(self, db: Session, target_date: Optional[str] = None, force_demo: bool = False) -> DailyMetrics:
        if not target_date:
            target_date = date.today().isoformat()

        client = None if force_demo else self.get_client()

        if client:
            try:
                metrics = self._fetch_live_metrics(client, target_date)
                self._last_sync_time = datetime.utcnow()
                logger.info(f"Successfully pulled live Garmin metrics for {target_date}")
            except Exception as e:
                logger.error(f"Error fetching live data for {target_date}: {e}")
                self._last_error = str(e)
                metrics = self._generate_empty_metrics(target_date)
        else:
            metrics = self._generate_empty_metrics(target_date)

        # Upsert into database
        db_metric = db.query(DailyMetrics).filter(DailyMetrics.date == target_date).first()
        if not db_metric:
            db_metric = DailyMetrics(date=target_date)
            db.add(db_metric)

        db_metric.steps = metrics.get("steps", 0)
        db_metric.step_goal = metrics.get("step_goal", 10000)
        db_metric.active_calories = metrics.get("active_calories", 0)
        db_metric.resting_calories = metrics.get("resting_calories", 1850)
        db_metric.total_calories_burned = db_metric.active_calories + db_metric.resting_calories
        db_metric.distance_meters = metrics.get("distance_meters", 0.0)
        db_metric.resting_heart_rate = metrics.get("resting_heart_rate")
        db_metric.sleep_seconds = metrics.get("sleep_seconds", 0)
        db_metric.sleep_score = metrics.get("sleep_score")
        db_metric.activities_json = json.dumps(metrics.get("activities", []))
        db_metric.raw_data_json = json.dumps(metrics.get("raw_data", {}))
        db_metric.synced_at = datetime.utcnow()

        db.commit()
        db.refresh(db_metric)
        return db_metric

    def _fetch_live_metrics(self, client, target_date: str) -> Dict[str, Any]:
        stats = client.get_stats(target_date) or {}
        
        # Sleep data
        sleep_data = {}
        try:
            sleep_data = client.get_sleep_data(target_date) or {}
        except Exception as e:
            logger.warning(f"Could not retrieve sleep data for {target_date}: {e}")

        # Activities for date
        activities_data = []
        try:
            activities = client.get_activities_by_date(target_date, target_date) or []
            for act in activities:
                activities_data.append({
                    "id": str(act.get("activityId")),
                    "name": act.get("activityName") or act.get("activityType", {}).get("typeKey", "Workout"),
                    "type": act.get("activityType", {}).get("typeKey", "general"),
                    "duration_mins": round(act.get("duration", 0) / 60, 1),
                    "distance_km": round(act.get("distance", 0) / 1000, 2),
                    "calories": int(act.get("calories", 0)),
                    "avg_hr": act.get("averageHR"),
                    "start_time": act.get("startTimeLocal", "")[11:16] if act.get("startTimeLocal") else None
                })
        except Exception as e:
            logger.warning(f"Could not retrieve activities for {target_date}: {e}")

        # Parse metrics
        steps = stats.get("totalSteps", 0)
        step_goal = stats.get("dailyStepGoal", 10000)
        active_cals = stats.get("activeKilocalories", 0)
        bmr_cals = stats.get("bmrKilocalories", 1850)
        distance = stats.get("totalDistanceMeters", 0.0)
        resting_hr = stats.get("restingHeartRate")
        
        # Sleep duration in seconds
        sleep_dto = sleep_data.get("dailySleepDTO", {})
        sleep_seconds = sleep_dto.get("sleepTimeSeconds", 0)
        sleep_score = sleep_dto.get("sleepScores", {}).get("overall", {}).get("value")

        return {
            "steps": steps,
            "step_goal": step_goal,
            "active_calories": active_cals,
            "resting_calories": bmr_cals,
            "distance_meters": distance,
            "resting_heart_rate": resting_hr,
            "sleep_seconds": sleep_seconds,
            "sleep_score": sleep_score,
            "activities": activities_data,
            "raw_data": {"stats": stats, "sleep": sleep_data}
        }

    def _generate_empty_metrics(self, target_date: str) -> Dict[str, Any]:
        """Returns clean empty metrics when Garmin live sync is not active."""
        return {
            "steps": 0,
            "step_goal": 10000,
            "active_calories": 0,
            "resting_calories": 1850,
            "distance_meters": 0.0,
            "resting_heart_rate": None,
            "sleep_seconds": 0,
            "sleep_score": None,
            "activities": [],
            "raw_data": {"synced": False, "error": self._last_error or "No live Garmin sync recorded"}
        }

garmin_service = GarminService()
