from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..database import Base

class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), unique=True, index=True, nullable=False) # YYYY-MM-DD
    summary = Column(Text, nullable=False)
    mood = Column(String(50), default="Neutral")
    health_summary = Column(Text, default="")
    nutrition_summary = Column(Text, default="")
    source_record_ids_json = Column(Text, default="[]") # JSON list of record ids rollup was built from
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        sources = []
        if self.source_record_ids_json:
            try:
                sources = json.loads(self.source_record_ids_json)
            except Exception:
                sources = []
        return {
            "id": self.id,
            "date": self.date,
            "summary": self.summary,
            "mood": self.mood,
            "health_summary": self.health_summary,
            "nutrition_summary": self.nutrition_summary,
            "source_record_ids": sources,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
