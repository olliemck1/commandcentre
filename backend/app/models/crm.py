from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    aliases = Column(Text, default="[]") # JSON list of strings
    first_met_date = Column(String(10), nullable=True) # YYYY-MM-DD
    last_seen_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    interaction_count = Column(Integer, default=0)
    notes_summary = Column(Text, default="")
    tags = Column(Text, default="[]") # JSON list of tags e.g. ["colleague", "runner"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interactions = relationship(
        "Interaction",
        back_populates="person",
        cascade="all, delete-orphan",
        order_by="desc(Interaction.date)"
    )

    def to_dict(self, include_interactions=False):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "aliases": json.loads(self.aliases or "[]"),
            "first_met_date": self.first_met_date,
            "last_seen_date": self.last_seen_date,
            "interaction_count": self.interaction_count,
            "notes_summary": self.notes_summary,
            "tags": json.loads(self.tags or "[]"),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_interactions and self.interactions:
            data["interactions"] = [i.to_dict() for i in self.interactions]
        return data


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    date = Column(String(10), index=True, nullable=False) # YYYY-MM-DD
    context_snippet = Column(Text, default="")
    sentiment = Column(String(50), default="neutral")
    location = Column(String(100), nullable=True)
    extracted_facts = Column(Text, default="[]") # JSON list of strings
    created_at = Column(DateTime, default=datetime.utcnow)

    person = relationship("Person", back_populates="interactions")
    journal_entry = relationship("JournalEntry", back_populates="interactions")

    def to_dict(self):
        return {
            "id": self.id,
            "person_id": self.person_id,
            "person_name": self.person.name if self.person else None,
            "journal_entry_id": self.journal_entry_id,
            "date": self.date,
            "context_snippet": self.context_snippet,
            "sentiment": self.sentiment,
            "location": self.location,
            "extracted_facts": json.loads(self.extracted_facts or "[]"),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
