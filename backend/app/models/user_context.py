from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..database import Base

class UserContext(Base):
    __tablename__ = "user_context"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False) # e.g. "goals", "preferences", "routines"
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "content": self.content,
            "version": self.version,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
