from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime
from ..database import Base

class DailyMetrics(Base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), unique=True, index=True, nullable=False) # YYYY-MM-DD
    steps = Column(Integer, default=0)
    step_goal = Column(Integer, default=10000)
    active_calories = Column(Integer, default=0)
    resting_calories = Column(Integer, default=0)
    total_calories_burned = Column(Integer, default=0)
    distance_meters = Column(Float, default=0.0)
    resting_heart_rate = Column(Integer, nullable=True)
    sleep_seconds = Column(Integer, default=0)
    sleep_score = Column(Integer, nullable=True)
    activities_json = Column(Text, default="[]")
    raw_data_json = Column(Text, default="{}")
    synced_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "date": self.date,
            "steps": self.steps,
            "step_goal": self.step_goal,
            "active_calories": self.active_calories,
            "resting_calories": self.resting_calories,
            "total_calories_burned": self.total_calories_burned,
            "distance_meters": self.distance_meters,
            "resting_heart_rate": self.resting_heart_rate,
            "sleep_seconds": self.sleep_seconds,
            "sleep_score": self.sleep_score,
            "activities": json.loads(self.activities_json or "[]"),
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
