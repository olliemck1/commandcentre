from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False) # e.g. COMP3001
    title = Column(String(150), nullable=False) # e.g. Distributed Systems & Cloud Computing
    term = Column(String(50), default="Autumn 2026")
    credits = Column(Integer, default=15)
    color = Column(String(20), default="#10b981") # Hex color for badges & visual tag
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    deadlines = relationship("Deadline", back_populates="module", cascade="all, delete-orphan", order_by="Deadline.due_date")
    tasks = relationship("AcademicTask", back_populates="module", cascade="all, delete-orphan")
    timetable_events = relationship("TimetableEvent", back_populates="module")

    def to_dict(self, include_counts=True):
        data = {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "term": self.term,
            "credits": self.credits,
            "color": self.color,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_counts:
            data["deadline_count"] = len(self.deadlines) if self.deadlines else 0
            data["pending_deadlines"] = len([d for d in (self.deadlines or []) if d.status != "submitted" and d.status != "graded"])
        return data


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    due_date = Column(String(30), nullable=False, index=True) # ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
    weight_percentage = Column(Float, default=0.0) # e.g. 40.0 for 40%
    status = Column(String(30), default="pending") # 'pending', 'submitted', 'graded'
    grade = Column(Float, nullable=True) # e.g. 82.5%
    priority = Column(String(20), default="Medium") # 'Low', 'Medium', 'High'
    resource_link = Column(String(300), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="deadlines")
    tasks = relationship("AcademicTask", back_populates="deadline", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "module_id": self.module_id,
            "module_code": self.module.code if self.module else None,
            "module_title": self.module.title if self.module else None,
            "module_color": self.module.color if self.module else "#10b981",
            "title": self.title,
            "due_date": self.due_date,
            "weight_percentage": self.weight_percentage,
            "status": self.status,
            "grade": self.grade,
            "priority": self.priority,
            "resource_link": self.resource_link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AcademicTask(Base):
    __tablename__ = "academic_tasks"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=True, index=True)
    deadline_id = Column(Integer, ForeignKey("deadlines.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    status = Column(String(20), default="todo") # 'todo', 'in_progress', 'done'
    priority = Column(String(20), default="medium") # 'low', 'medium', 'high'
    due_date = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="tasks")
    deadline = relationship("Deadline", back_populates="tasks")

    def to_dict(self):
        return {
            "id": self.id,
            "module_id": self.module_id,
            "module_code": self.module.code if self.module else None,
            "deadline_id": self.deadline_id,
            "deadline_title": self.deadline.title if self.deadline else None,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TimetableEvent(Base):
    __tablename__ = "timetable_events"

    id = Column(Integer, primary_key=True, index=True)
    sync_id = Column(String(200), unique=True, index=True, nullable=False) # UID from iCal or Mongo _id/syncId
    source = Column(String(50), default="mytimetable") # 'mytimetable', 'blackboard', 'mongodb', 'manual'
    title = Column(String(250), nullable=False)
    subject = Column(String(150), default="") # e.g. CLC202, PH8, or course name
    location = Column(String(150), default="")
    start_time = Column(String(40), index=True, nullable=False) # ISO timestamp
    end_time = Column(String(40), nullable=True) # ISO timestamp
    event_type = Column(String(50), default="lecture") # 'lecture', 'drop-in', 'tutorial', 'practical', 'office-hours', 'event'
    module_code = Column(String(50), index=True, nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text, default="")
    status = Column(String(30), default="scheduled")
    raw_data = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="timetable_events")

    def to_dict(self):
        import json
        raw = {}
        if self.raw_data:
            try:
                raw = json.loads(self.raw_data)
            except Exception:
                raw = {}

        priority = raw.get("priority") or "Medium"
        res_link = raw.get("resourceLink") or raw.get("resource_link") or ""
        if not res_link and self.location and self.location.startswith("http"):
            res_link = self.location

        # Normalize display status
        display_status = self.status or "scheduled"
        if display_status.lower() in ["completed", "submitted", "done"]:
            display_status = "Completed"
        elif display_status.lower() in ["scheduled", "not started", "pending"]:
            display_status = "Not Started"

        return {
            "id": self.id,
            "_id": str(self.id),
            "sync_id": self.sync_id,
            "syncId": self.sync_id,
            "source": self.source or "mytimetable",
            "title": self.title,
            "subject": self.subject or self.location or "University",
            "location": self.location or "",
            "start_time": self.start_time,
            "end_time": self.end_time or self.start_time,
            "startDate": self.start_time,
            "endDate": self.end_time or self.start_time,
            "dueDate": self.end_time or self.start_time,
            "priority": priority,
            "status": display_status,
            "resourceLink": res_link,
            "event_type": self.event_type or "lecture",
            "module_code": self.module_code or (self.module.code if self.module else None),
            "module_id": self.module_id,
            "module_color": self.module.color if self.module else "#6366f1",
            "module_title": self.module.title if self.module else None,
            "description": self.description or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

