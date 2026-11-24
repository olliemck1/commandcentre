from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from ..database import Base

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False)
    due_at = Column(String(40), index=True, nullable=False) # ISO timestamp or YYYY-MM-DD HH:MM
    status = Column(String(30), default="pending", index=True) # pending, sent, cancelled
    cron_or_time = Column(String(50), nullable=True) # e.g. cron string if recurring
    sent_at = Column(DateTime, nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "due_at": self.due_at,
            "status": self.status,
            "cron_or_time": self.cron_or_time,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
