import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..models.journal import JournalEntry
from ..models.nutrition import NutritionLog
from ..models.daily_metrics import DailyMetrics
from ..models.crm import Person, Interaction
from ..models.university import Module, Deadline, AcademicTask, TimetableEvent

logger = logging.getLogger("agent_tools")

# Tool 1: Query Journal
def query_journal(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 5
) -> Dict[str, Any]:
    query = db.query(JournalEntry)
    if start_date:
        query = query.filter(JournalEntry.date >= start_date)
    if end_date:
        query = query.filter(JournalEntry.date <= end_date)
    if keyword:
        k = f"%{keyword.lower()}%"
        query = query.filter(
            or_(
                func.lower(JournalEntry.raw_text).like(k),
                func.lower(JournalEntry.summary).like(k),
                func.lower(JournalEntry.tags_json).like(k)
            )
        )

    entries = query.order_by(JournalEntry.date.desc()).limit(limit).all()
    results = []
    citations = []
    for e in entries:
        d = e.to_dict()
        results.append(d)
        citations.append({
            "type": "journal",
            "id": f"journal-{e.id}",
            "title": f"Journal Entry ({e.date})",
            "snippet": e.summary or (e.raw_text[:120] + "..."),
            "date": e.date
        })

    return {
        "count": len(results),
        "entries": results,
        "citations": citations
    }

# Tool 2: Person Dossier
def get_person_dossier(db: Session, person_name: str) -> Dict[str, Any]:
    name_clean = person_name.lower().strip()
    person = db.query(Person).filter(
        or_(
            func.lower(Person.name) == name_clean,
            Person.slug == name_clean,
            func.lower(Person.aliases).like(f"%{name_clean}%")
        )
    ).first()

    if not person:
        # Partial match
        person = db.query(Person).filter(func.lower(Person.name).like(f"%{name_clean}%")).first()

    if not person:
        return {
            "found": False,
            "message": f"No person record found matching '{person_name}'.",
            "citations": []
        }

    detail = person.to_dict(include_interactions=True)
    citations = [{
        "type": "person",
        "id": f"person-{person.id}",
        "title": f"CRM Contact: {person.name}",
        "snippet": person.notes_summary[:120] if person.notes_summary else f"Last seen: {person.last_seen_date}",
        "date": person.last_seen_date
    }]

    for inter in detail.get("interactions", [])[:3]:
        citations.append({
            "type": "interaction",
            "id": f"interaction-{inter['id']}",
            "title": f"Interaction with {person.name} ({inter['date']})",
            "snippet": inter["context_snippet"][:120],
            "date": inter["date"]
        })

    return {
        "found": True,
        "person": detail,
        "citations": citations
    }

# Tool 3: Garmin Metrics
def get_garmin_metrics(db: Session, target_date: Optional[str] = None) -> Dict[str, Any]:
    if not target_date:
        target_date = date.today().isoformat()

    metric = db.query(DailyMetrics).filter(DailyMetrics.date == target_date).first()
    if not metric:
        return {
            "found": False,
            "date": target_date,
            "message": f"No Garmin telemetry logged for {target_date}.",
            "citations": []
        }

    data = metric.to_dict()
    citations = [{
        "type": "garmin",
        "id": f"garmin-{target_date}",
        "title": f"Garmin Telemetry ({target_date})",
        "snippet": f"{data['steps']:,} steps, {data['total_calories_burned']} kcal burned, {data['sleep_seconds']//3600}h sleep",
        "date": target_date
    }]

    return {
        "found": True,
        "date": target_date,
        "metrics": data,
        "citations": citations
    }

# Tool 4: Upcoming Deadlines
def get_upcoming_deadlines(
    db: Session,
    days_ahead: int = 14,
    module_code: Optional[str] = None
) -> Dict[str, Any]:
    today_str = date.today().isoformat()
    future_str = (date.today() + timedelta(days=days_ahead)).isoformat()

    query = db.query(Deadline)
    if module_code:
        query = query.join(Module).filter(func.lower(Module.code) == module_code.lower())

    query = query.filter(Deadline.due_date >= today_str, Deadline.due_date <= future_str)
    deadlines = query.order_by(Deadline.due_date.asc()).all()

    results = [d.to_dict() for d in deadlines]
    citations = []
    for d in deadlines:
        citations.append({
            "type": "deadline",
            "id": f"deadline-{d.id}",
            "title": f"Deadline: {d.title} ({d.module.code if d.module else 'Uni'})",
            "snippet": f"Due {d.due_date} • Weight: {d.weight_percentage}% • Priority: {d.priority}",
            "date": d.due_date
        })

    return {
        "count": len(results),
        "days_window": days_ahead,
        "deadlines": results,
        "citations": citations
    }

# Tool 5: Academic Tasks
def get_academic_tasks(
    db: Session,
    status: Optional[str] = None,
    module_code: Optional[str] = None
) -> Dict[str, Any]:
    query = db.query(AcademicTask)
    if status:
        query = query.filter(AcademicTask.status == status)
    if module_code:
        query = query.join(Module).filter(func.lower(Module.code) == module_code.lower())

    tasks = query.order_by(AcademicTask.created_at.desc()).limit(10).all()
    results = [t.to_dict() for t in tasks]
    citations = []
    for t in tasks:
        citations.append({
            "type": "task",
            "id": f"task-{t.id}",
            "title": f"Study Task: {t.title}",
            "snippet": f"Status: {t.status} • Priority: {t.priority}",
            "date": t.due_date
        })

    return {
        "count": len(results),
        "tasks": results,
        "citations": citations
    }

# Tool 6: Nutrition Summary
def get_nutrition_summary(db: Session, target_date: Optional[str] = None) -> Dict[str, Any]:
    if not target_date:
        target_date = date.today().isoformat()

    logs = db.query(NutritionLog).filter(NutritionLog.date == target_date).all()
    if not logs:
        # Fallback to journal entry nutrition json
        journal = db.query(JournalEntry).filter(JournalEntry.date == target_date).first()
        if journal and journal.nutrition_json:
            nut = json.loads(journal.nutrition_json)
            citations = [{
                "type": "nutrition",
                "id": f"nutrition-{target_date}",
                "title": f"Nutrition Log ({target_date})",
                "snippet": f"Total: {nut.get('total_calories', 0)} kcal, P:{nut.get('total_protein_g', 0)}g, C:{nut.get('total_carbs_g', 0)}g, F:{nut.get('total_fat_g', 0)}g",
                "date": target_date
            }]
            return {
                "date": target_date,
                "total_calories": nut.get("total_calories", 0),
                "protein_g": nut.get("total_protein_g", 0),
                "carbs_g": nut.get("total_carbs_g", 0),
                "fat_g": nut.get("total_fat_g", 0),
                "items": nut.get("items", []),
                "citations": citations
            }

        return {
            "date": target_date,
            "total_calories": 0,
            "message": f"No nutrition records logged for {target_date}.",
            "citations": []
        }

    total_cals = sum(l.estimated_calories for l in logs)
    total_p = round(sum(l.protein for l in logs), 1)
    total_c = round(sum(l.carbs for l in logs), 1)
    total_f = round(sum(l.fat for l in logs), 1)

    items = [{"name": l.item_name, "portion": l.portion, "calories": l.estimated_calories, "protein": l.protein, "carbs": l.carbs, "fat": l.fat} for l in logs]
    citations = [{
        "type": "nutrition",
        "id": f"nutrition-{target_date}",
        "title": f"Nutrition Log ({target_date})",
        "snippet": f"{len(logs)} foods logged • {total_cals} total kcal (P:{total_p}g, C:{total_c}g, F:{total_f}g)",
        "date": target_date
    }]

    return {
        "date": target_date,
        "total_calories": total_cals,
        "protein_g": total_p,
        "carbs_g": total_c,
        "fat_g": total_f,
        "items": items,
        "citations": citations
    }

# Tool 7: University Timetable & Classes
def get_university_timetable(
    db: Session,
    target_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    module_code: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    query = db.query(TimetableEvent)
    if target_date:
        query = query.filter(TimetableEvent.start_time.startswith(target_date))
    elif start_date or end_date:
        if start_date:
            query = query.filter(TimetableEvent.start_time >= start_date)
        if end_date:
            query = query.filter(TimetableEvent.start_time <= end_date)
    else:
        # Default to upcoming from today
        now_str = date.today().isoformat()
        query = query.filter(TimetableEvent.start_time >= now_str)

    if module_code:
        query = query.filter(func.lower(TimetableEvent.module_code) == module_code.lower())

    events = query.order_by(TimetableEvent.start_time.asc()).limit(limit).all()
    results = [e.to_dict() for e in events]
    citations = []
    for e in events:
        loc = e.location or e.subject or "Campus"
        citations.append({
            "type": "timetable",
            "id": f"timetable-{e.id}",
            "title": f"Timetable: {e.title}",
            "snippet": f"{e.event_type.capitalize()} at {loc} ({e.start_time[:16].replace('T', ' ')})",
            "date": e.start_time[:10]
        })

    return {
        "count": len(results),
        "events": results,
        "citations": citations
    }

# Tool declarations schema for LLM function calling (OpenAI & Gemini format)
TOOL_DEFINITIONS = [
    {
        "name": "query_journal",
        "description": "Searches daily journal entries by date range or keyword.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD start date"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD end date"},
                "keyword": {"type": "string", "description": "Search keyword"}
            }
        }
    },
    {
        "name": "get_person_dossier",
        "description": "Retrieves contact info, learned personal facts/preferences, and interaction history for an individual.",
        "parameters": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string", "description": "First or full name of the person (e.g. Sam, Alex, Sarah)"}
            },
            "required": ["person_name"]
        }
    },
    {
        "name": "get_garmin_metrics",
        "description": "Fetches physical activity metrics from Garmin: steps, active calories, resting calories, distance, resting HR, and sleep duration.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_date": {"type": "string", "description": "YYYY-MM-DD date"}
            }
        }
    },
    {
        "name": "get_upcoming_deadlines",
        "description": "Retrieves upcoming university coursework, assignments, and exam deadlines.",
        "parameters": {
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "description": "Days into future to check (default 14)"},
                "module_code": {"type": "string", "description": "Optional module code filter, e.g. COMP3001"}
            }
        }
    },
    {
        "name": "get_academic_tasks",
        "description": "Fetches university academic study tasks and checklists.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "'todo', 'in_progress', or 'done'"},
                "module_code": {"type": "string", "description": "Optional module code filter"}
            }
        }
    },
    {
        "name": "get_nutrition_summary",
        "description": "Fetches dietary intake, total calories, and macronutrient breakdown (protein, carbs, fat) for a given date.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_date": {"type": "string", "description": "YYYY-MM-DD date"}
            }
        }
    },
    {
        "name": "get_university_timetable",
        "description": "Fetches university lecture timetable, tutorials, drop-ins, and classroom schedule with locations.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_date": {"type": "string", "description": "Specific day YYYY-MM-DD"},
                "start_date": {"type": "string", "description": "Start ISO date"},
                "end_date": {"type": "string", "description": "End ISO date"},
                "module_code": {"type": "string", "description": "Optional module code e.g. COMP2221"},
                "limit": {"type": "integer", "description": "Maximum events to return (default 10)"}
            }
        }
    }
]
