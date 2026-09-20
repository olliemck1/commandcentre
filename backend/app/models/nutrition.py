from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), index=True, nullable=False) # YYYY-MM-DD
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=True, index=True)
    item_name = Column(String(150), nullable=False)
    portion = Column(String(100), default="1 serving")
    estimated_calories = Column(Integer, default=0)
    protein = Column(Float, default=0.0) # grams
    carbs = Column(Float, default=0.0)   # grams
    fat = Column(Float, default=0.0)     # grams
    confidence = Column(Float, default=0.85)
    created_at = Column(DateTime, default=datetime.utcnow)

    journal_entry = relationship("JournalEntry", back_populates="nutrition_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "journal_entry_id": self.journal_entry_id,
            "item_name": self.item_name,
            "portion": self.portion,
            "estimated_calories": self.estimated_calories,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
