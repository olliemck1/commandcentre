from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from ..database import Base

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), index=True, nullable=False) # YYYY-MM-DD
    raw_text = Column(Text, nullable=False)
    summary = Column(Text, default="")
    mood = Column(String(50), default="Neutral")
    nutrition_json = Column(Text, default="{}")
    people_json = Column(Text, default="[]")
    tags_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="journal_entry")
    nutrition_logs = relationship("NutritionLog", back_populates="journal_entry", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "raw_text": self.raw_text,
            "summary": self.summary,
            "mood": self.mood,
            "nutrition": json.loads(self.nutrition_json or "{}"),
            "people": json.loads(self.people_json or "[]"),
            "tags": json.loads(self.tags_json or "[]"),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
