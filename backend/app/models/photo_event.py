from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from ..database import Base

class PhotoEvent(Base):
    __tablename__ = "photo_events"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(150), unique=True, index=True, nullable=True) # Immich / icloudpd asset ID
    timestamp = Column(String(40), index=True, nullable=False) # ISO timestamp
    date = Column(String(10), index=True, nullable=False) # YYYY-MM-DD
    title = Column(String(200), default="")
    description = Column(Text, default="")
    location_name = Column(String(150), default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    tags_json = Column(Text, default="[]")
    people_json = Column(Text, default="[]")
    thumbnail_path = Column(String(300), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        tags = []
        people = []
        if self.tags_json:
            try:
                tags = json.loads(self.tags_json)
            except Exception:
                tags = []
        if self.people_json:
            try:
                people = json.loads(self.people_json)
            except Exception:
                people = []
        return {
            "id": self.id,
            "external_id": self.external_id,
            "timestamp": self.timestamp,
            "date": self.date,
            "title": self.title,
            "description": self.description,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "tags": tags,
            "people": people,
            "thumbnail_path": self.thumbnail_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
