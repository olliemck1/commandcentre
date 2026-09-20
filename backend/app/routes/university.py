from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models.university import Module, Deadline, AcademicTask, TimetableEvent
from ..schemas.university import (
    ModuleCreate,
    ModuleResponse,
    DeadlineCreate,
    DeadlineUpdate,
    DeadlineResponse,
    AcademicTaskCreate,
    AcademicTaskUpdate,
    AcademicTaskResponse,
)
from ..schemas.timetable import (
    TimetableEventResponse,
    TimetableSyncRequest,
    TimetableSyncResponse,
    TimetableCreateRequest,
    TimetableUpdateRequest,
)
from ..services.timetable_service import timetable_service

router = APIRouter(prefix="/api", tags=["university"])

# ----------------- MODULES -----------------

@router.get("/modules", response_model=List[ModuleResponse])
def get_modules(db: Session = Depends(get_db)):
    modules = db.query(Module).order_by(Module.code).all()
    return [m.to_dict(include_counts=True) for m in modules]

@router.post("/modules", response_model=ModuleResponse)
def create_module(req: ModuleCreate, db: Session = Depends(get_db)):
    existing = db.query(Module).filter(Module.code == req.code.upper().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Module with code {req.code} already exists")

    module = Module(
        code=req.code.upper().strip(),
        title=req.title.strip(),
        term=req.term,
        credits=req.credits,
        color=req.color,
        description=req.description,
        created_at=datetime.utcnow()
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module.to_dict(include_counts=True)

@router.delete("/modules/{module_id}")
def delete_module(module_id: int, db: Session = Depends(get_db)):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    db.delete(module)
    db.commit()
    return {"message": "Module deleted"}

# ----------------- DEADLINES -----------------

@router.get("/deadlines", response_model=List[DeadlineResponse])
def get_deadlines(
    module_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Deadline)
    if module_id:
        query = query.filter(Deadline.module_id == module_id)
    if status:
        query = query.filter(Deadline.status == status)

    deadlines = query.order_by(Deadline.due_date.asc()).all()
    return [d.to_dict() for d in deadlines]

@router.post("/deadlines", response_model=DeadlineResponse)
def create_deadline(req: DeadlineCreate, db: Session = Depends(get_db)):
    module = db.query(Module).filter(Module.id == req.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    deadline = Deadline(
        module_id=req.module_id,
        title=req.title.strip(),
        due_date=req.due_date,
        weight_percentage=req.weight_percentage,
        status=req.status,
        grade=req.grade,
        priority=req.priority,
        resource_link=req.resource_link,
        created_at=datetime.utcnow()
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline.to_dict()

@router.put("/deadlines/{deadline_id}", response_model=DeadlineResponse)
def update_deadline(deadline_id: int, req: DeadlineUpdate, db: Session = Depends(get_db)):
    deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    if req.title is not None:
        deadline.title = req.title.strip()
    if req.module_id is not None:
        deadline.module_id = req.module_id
    if req.due_date is not None:
        deadline.due_date = req.due_date
    if req.weight_percentage is not None:
        deadline.weight_percentage = req.weight_percentage
    if req.status is not None:
        deadline.status = req.status
    if req.grade is not None:
        deadline.grade = req.grade
    if req.priority is not None:
        deadline.priority = req.priority
    if req.resource_link is not None:
        deadline.resource_link = req.resource_link

    db.commit()
    db.refresh(deadline)
    return deadline.to_dict()

@router.delete("/deadlines/{deadline_id}")
def delete_deadline(deadline_id: int, db: Session = Depends(get_db)):
    deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    db.delete(deadline)
    db.commit()
    return {"message": "Deadline deleted"}

# ----------------- ACADEMIC TASKS -----------------

@router.get("/tasks", response_model=List[AcademicTaskResponse])
def get_tasks(
    module_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(AcademicTask)
    if module_id:
        query = query.filter(AcademicTask.module_id == module_id)
    if status:
        query = query.filter(AcademicTask.status == status)

    tasks = query.order_by(AcademicTask.created_at.desc()).all()
    return [t.to_dict() for t in tasks]

@router.post("/tasks", response_model=AcademicTaskResponse)
def create_task(req: AcademicTaskCreate, db: Session = Depends(get_db)):
    task = AcademicTask(
        module_id=req.module_id,
        deadline_id=req.deadline_id,
        title=req.title.strip(),
        status=req.status,
        priority=req.priority,
        due_date=req.due_date,
        created_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task.to_dict()

@router.put("/tasks/{task_id}", response_model=AcademicTaskResponse)
def update_task(task_id: int, req: AcademicTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(AcademicTask).filter(AcademicTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if req.title is not None:
        task.title = req.title.strip()
    if req.status is not None:
        task.status = req.status
    if req.priority is not None:
        task.priority = req.priority
    if req.due_date is not None:
        task.due_date = req.due_date
    if req.module_id is not None:
        task.module_id = req.module_id
    if req.deadline_id is not None:
        task.deadline_id = req.deadline_id

    db.commit()
    db.refresh(task)
    return task.to_dict()

@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(AcademicTask).filter(AcademicTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


# ----------------- TIMETABLE & SCHEDULE -----------------

@router.get("/timetable", response_model=List[TimetableEventResponse])
def get_timetable_events(
    date: Optional[str] = Query(None, description="Exact day YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date ISO"),
    end_date: Optional[str] = Query(None, description="End date ISO"),
    module_code: Optional[str] = Query(None, description="Module code e.g. COMP2221"),
    source: Optional[str] = Query(None, description="Filter by source e.g. mytimetable"),
    upcoming_only: bool = Query(False, description="Filter to future events only"),
    limit: int = Query(2500, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    events = timetable_service.get_events(
        db=db,
        target_date=date,
        start_date=start_date,
        end_date=end_date,
        module_code=module_code,
        source=source,
        upcoming_only=upcoming_only,
        limit=limit
    )
    return [e.to_dict() for e in events]


@router.put("/timetable/{event_id}", response_model=TimetableEventResponse)
def update_timetable_event(
    event_id: int,
    req: TimetableUpdateRequest,
    db: Session = Depends(get_db)
):
    ev = db.query(TimetableEvent).filter(TimetableEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Timetable event not found")

    if req.title is not None:
        ev.title = req.title.strip()
    if req.status is not None:
        ev.status = req.status
    if req.subject is not None:
        ev.subject = req.subject
    if req.location is not None:
        ev.location = req.location

    # Update raw_data for priority/resourceLink if provided
    import json
    raw = {}
    if ev.raw_data:
        try:
            raw = json.loads(ev.raw_data)
        except Exception:
            raw = {}

    if req.priority is not None:
        raw["priority"] = req.priority
    if req.resourceLink is not None:
        raw["resourceLink"] = req.resourceLink
    ev.raw_data = json.dumps(raw)

    db.commit()
    db.refresh(ev)
    return ev.to_dict()


@router.delete("/timetable/{event_id}")
def delete_timetable_event(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(TimetableEvent).filter(TimetableEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Timetable event not found")
    db.delete(ev)
    db.commit()
    return {"message": "Timetable event deleted"}


@router.post("/timetable/sync/ical", response_model=TimetableSyncResponse)
def sync_timetable_ical(
    req: Optional[TimetableSyncRequest] = None,
    db: Session = Depends(get_db)
):
    sources = None
    if req and req.ical_url:
        sources = [{"url": req.ical_url, "name": req.source_name or "custom_ical"}]
    res = timetable_service.sync_ical_feeds(db=db, sources=sources)
    return res


@router.post("/timetable/sync/mongodb", response_model=TimetableSyncResponse)
def sync_timetable_mongodb(
    req: Optional[TimetableSyncRequest] = None,
    db: Session = Depends(get_db)
):
    mongo_uri = req.mongodb_uri if req else None
    res = timetable_service.sync_from_mongodb(db=db, mongo_uri=mongo_uri)
    return res


@router.get("/timetable/status")
def get_timetable_status(db: Session = Depends(get_db)):
    return timetable_service.get_status(db=db)


@router.post("/timetable", response_model=TimetableEventResponse)
def create_manual_timetable_event(
    req: TimetableCreateRequest,
    db: Session = Depends(get_db)
):
    module_id = None
    if req.module_code:
        mod = timetable_service.ensure_module(db, req.module_code)
        module_id = mod.id

    import uuid
    sync_id = f"manual_{uuid.uuid4().hex[:12]}"
    ev = TimetableEvent(
        sync_id=sync_id,
        source="manual",
        title=req.title.strip(),
        subject=req.subject or req.location or "Manual Entry",
        location=req.location or "",
        start_time=req.start_time,
        end_time=req.end_time or req.start_time,
        event_type=req.event_type or "class",
        module_code=req.module_code,
        module_id=module_id,
        description=req.description or "",
        status="Not Started"
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev.to_dict()


# ----------------- UNIFIED ASSIGNMENTS API (Personal Dashboard Compat) -----------------

@router.get("/assignments")
def get_assignments(
    tab: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns unified assignments and schedule items compatible with the personal dashboard.
    """
    events = timetable_service.get_events(db=db, limit=3000)
    items = [e.to_dict() for e in events]
    return items


@router.post("/assignments")
def create_assignment(
    req: dict,
    db: Session = Depends(get_db)
):
    import uuid
    sync_id = f"manual_{uuid.uuid4().hex[:12]}"
    title = req.get("title", "New Task").strip()
    subject = req.get("subject", "University").strip()
    due_date = req.get("dueDate") or req.get("startDate") or datetime.utcnow().isoformat()
    priority = req.get("priority", "Medium")
    source = req.get("source", "manual")
    resource_link = req.get("resourceLink", "")

    import json
    raw = json.dumps({"priority": priority, "resourceLink": resource_link})

    ev = TimetableEvent(
        sync_id=sync_id,
        source=source,
        title=title,
        subject=subject,
        location=subject,
        start_time=due_date,
        end_time=due_date,
        event_type="assignment",
        description="Created from Deadlines & Tasks",
        status="Not Started",
        raw_data=raw
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev.to_dict()


@router.put("/assignments/{assignment_id}")
def update_assignment(
    assignment_id: str,
    req: dict,
    db: Session = Depends(get_db)
):
    ev = None
    # Try by numeric id first, then sync_id
    if assignment_id.isdigit():
        ev = db.query(TimetableEvent).filter(TimetableEvent.id == int(assignment_id)).first()
    if not ev:
        ev = db.query(TimetableEvent).filter(TimetableEvent.sync_id == assignment_id).first()

    if not ev:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if "title" in req:
        ev.title = str(req["title"]).strip()
    if "status" in req:
        ev.status = str(req["status"])
    if "subject" in req:
        ev.subject = str(req["subject"])

    import json
    raw = {}
    if ev.raw_data:
        try:
            raw = json.loads(ev.raw_data)
        except Exception:
            raw = {}

    if "priority" in req:
        raw["priority"] = req["priority"]
    if "resourceLink" in req:
        raw["resourceLink"] = req["resourceLink"]
    ev.raw_data = json.dumps(raw)

    db.commit()
    db.refresh(ev)
    return ev.to_dict()


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db)
):
    ev = None
    if assignment_id.isdigit():
        ev = db.query(TimetableEvent).filter(TimetableEvent.id == int(assignment_id)).first()
    if not ev:
        ev = db.query(TimetableEvent).filter(TimetableEvent.sync_id == assignment_id).first()

    if not ev:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(ev)
    db.commit()
    return {"message": "Assignment deleted successfully"}


@router.post("/calendar/sync")
def sync_calendars_compat(db: Session = Depends(get_db)):
    res = timetable_service.sync_ical_feeds(db=db)
    return {
        "success": True,
        "message": f"Durham feeds synced: {res.get('total_processed', 0)} events processed ({res.get('new_events', 0)} new, {res.get('updated_events', 0)} updated)."
    }

