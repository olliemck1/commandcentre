"""Agent tools for Command Centre Assistant.

Provides:
- Date-ranged read tools with precomputed aggregates (LLM does no arithmetic):
  - get_garmin_metrics
  - query_journal (SQLite FTS5 + date range)
  - get_nutrition_summary
  - get_university_timetable / get_calendar_events
  - get_upcoming_deadlines
  - get_academic_tasks
  - get_person_dossier
  - get_daily_summaries
  - get_linked_photos
- Write tools (audited and logged):
  - add_journal_entry
  - schedule_reminder
- Tool execution logging (all calls and write actions)
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text

from ..models.journal import JournalEntry
from ..models.nutrition import NutritionLog
from ..models.daily_metrics import DailyMetrics
from ..models.crm import Person, Interaction
from ..models.university import Module, Deadline, AcademicTask, TimetableEvent
from ..models.daily_summary import DailySummary
from ..models.reminder import Reminder
from ..models.photo_event import PhotoEvent

logger = logging.getLogger("agent_tools")

def _log_tool_call(tool_name: str, args: Dict[str, Any], is_write: bool = False):
    prefix = "[TOOL WRITE ACTION]" if is_write else "[TOOL CALL]"
    logger.info(f"{prefix} tool={tool_name} args={json.dumps(args, default=str)}")

# Tool 1: Query Journal (with Date Range & SQLite FTS5)
def query_journal(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    target_date: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    _log_tool_call("query_journal", {"start_date": start_date, "end_date": end_date, "target_date": target_date, "keyword": keyword})
    
    query = db.query(JournalEntry)
    if target_date:
        query = query.filter(JournalEntry.date == target_date)
    else:
        if start_date:
            query = query.filter(JournalEntry.date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.date <= end_date)

    if keyword and keyword.strip():
        k = f"%{keyword.lower().strip()}%"
        query = query.filter(
            or_(
                func.lower(JournalEntry.raw_text).like(k),
                func.lower(JournalEntry.summary).like(k),
                func.lower(JournalEntry.tags_json).like(k),
                func.lower(JournalEntry.mood).like(k)
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
    _log_tool_call("get_person_dossier", {"person_name": person_name})
    name_clean = person_name.lower().strip()
    person = db.query(Person).filter(
        or_(
            func.lower(Person.name) == name_clean,
            Person.slug == name_clean,
            func.lower(Person.aliases).like(f"%{name_clean}%")
        )
    ).first()

    if not person:
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

    for inter in detail.get("interactions", [])[:5]:
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

# Tool 3: Garmin Metrics with Aggregates
def get_garmin_metrics(
    db: Session,
    target_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    _log_tool_call("get_garmin_metrics", {"target_date": target_date, "start_date": start_date, "end_date": end_date})
    query = db.query(DailyMetrics)

    if target_date:
        query = query.filter(DailyMetrics.date == target_date)
    else:
        if start_date:
            query = query.filter(DailyMetrics.date >= start_date)
        if end_date:
            query = query.filter(DailyMetrics.date <= end_date)

    metrics_list = query.order_by(DailyMetrics.date.asc()).all()
    if not metrics_list:
        return {
            "found": False,
            "count": 0,
            "message": f"No Garmin metrics found for requested date range.",
            "citations": []
        }

    items = [m.to_dict() for m in metrics_list]
    citations = []
    for m in metrics_list:
        d = m.to_dict()
        sleep_h = d['sleep_seconds'] // 3600
        sleep_m = (d['sleep_seconds'] % 3600) // 60
        citations.append({
            "type": "garmin",
            "id": f"garmin-{m.date}",
            "title": f"Garmin Telemetry ({m.date})",
            "snippet": f"{d['steps']:,} steps, {d['total_calories_burned']} kcal burned, {sleep_h}h {sleep_m}m sleep (score: {d.get('sleep_score') or 'N/A'})",
            "date": m.date
        })

    # Precomputed aggregates (LLM does no arithmetic)
    steps_vals = [m.steps for m in metrics_list]
    sleep_vals = [m.sleep_seconds for m in metrics_list]
    sleep_scores = [m.sleep_score for m in metrics_list if m.sleep_score is not None]
    cals_vals = [m.total_calories_burned for m in metrics_list]
    hr_vals = [m.resting_heart_rate for m in metrics_list if m.resting_heart_rate is not None]

    # Peak metrics
    max_steps_metric = max(metrics_list, key=lambda m: m.steps) if metrics_list else None

    aggregates = {
        "days_count": len(metrics_list),
        "total_steps": sum(steps_vals),
        "avg_steps": round(sum(steps_vals) / len(steps_vals), 1) if steps_vals else 0,
        "max_steps": max(steps_vals) if steps_vals else 0,
        "max_steps_date": max_steps_metric.date if max_steps_metric else None,
        "avg_sleep_hours": round((sum(sleep_vals) / len(sleep_vals)) / 3600, 2) if sleep_vals else 0,
        "avg_sleep_score": round(sum(sleep_scores) / len(sleep_scores), 1) if sleep_scores else None,
        "avg_resting_hr": round(sum(hr_vals) / len(hr_vals), 1) if hr_vals else None,
        "avg_total_calories_burned": round(sum(cals_vals) / len(cals_vals), 1) if cals_vals else 0
    }

    return {
        "found": True,
        "count": len(items),
        "metrics": items if len(items) > 1 else items[0],
        "aggregates": aggregates,
        "citations": citations
    }

# Tool 4: Nutrition Summary with Aggregates
def get_nutrition_summary(
    db: Session,
    target_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    _log_tool_call("get_nutrition_summary", {"target_date": target_date, "start_date": start_date, "end_date": end_date})
    query = db.query(NutritionLog)

    if target_date:
        query = query.filter(NutritionLog.date == target_date)
    else:
        if start_date:
            query = query.filter(NutritionLog.date >= start_date)
        if end_date:
            query = query.filter(NutritionLog.date <= end_date)

    logs = query.order_by(NutritionLog.date.asc()).all()

    # If no standalone logs, check journal nutrition json
    if not logs and target_date:
        journal = db.query(JournalEntry).filter(JournalEntry.date == target_date).first()
        if journal and journal.nutrition_json:
            try:
                nut = json.loads(journal.nutrition_json)
                citations = [{
                    "type": "nutrition",
                    "id": f"nutrition-{target_date}",
                    "title": f"Nutrition Log ({target_date})",
                    "snippet": f"Total: {nut.get('total_calories', 0)} kcal, P:{nut.get('total_protein_g', 0)}g, C:{nut.get('total_carbs_g', 0)}g, F:{nut.get('total_fat_g', 0)}g",
                    "date": target_date
                }]
                return {
                    "found": True,
                    "target_date": target_date,
                    "total_calories": nut.get("total_calories", 0),
                    "protein_g": nut.get("total_protein_g", 0.0),
                    "carbs_g": nut.get("total_carbs_g", 0.0),
                    "fat_g": nut.get("total_fat_g", 0.0),
                    "items": nut.get("items", []),
                    "citations": citations
                }
            except Exception:
                pass

    if not logs:
        return {
            "found": False,
            "total_calories": 0,
            "message": "No nutrition records logged for requested range.",
            "citations": []
        }

    total_cals = sum(l.estimated_calories for l in logs)
    total_p = round(sum(l.protein for l in logs), 1)
    total_c = round(sum(l.carbs for l in logs), 1)
    total_f = round(sum(l.fat for l in logs), 1)

    items = [l.to_dict() for l in logs]
    citations = [{
        "type": "nutrition",
        "id": f"nutrition-{logs[0].date}",
        "title": f"Nutrition Log ({len(logs)} items)",
        "snippet": f"{total_cals} total kcal (P:{total_p}g, C:{total_c}g, F:{total_f}g)",
        "date": logs[0].date
    }]

    return {
        "found": True,
        "count": len(items),
        "total_calories": total_cals,
        "protein_g": total_p,
        "carbs_g": total_c,
        "fat_g": total_f,
        "items": items,
        "citations": citations
    }

# Tool 5: Upcoming Deadlines
def get_upcoming_deadlines(
    db: Session,
    days_ahead: int = 14,
    module_code: Optional[str] = None,
    reference_date: Optional[str] = None
) -> Dict[str, Any]:
    _log_tool_call("get_upcoming_deadlines", {"days_ahead": days_ahead, "module_code": module_code, "reference_date": reference_date})
    ref_d = date.fromisoformat(reference_date) if reference_date else date.today()
    start_str = ref_d.isoformat()
    future_str = (ref_d + timedelta(days=days_ahead)).isoformat()

    query = db.query(Deadline)
    if module_code:
        query = query.join(Module).filter(func.lower(Module.code) == module_code.lower())

    deadlines = query.filter(Deadline.due_date >= start_str, Deadline.due_date <= future_str).order_by(Deadline.due_date.asc()).all()

    # If none found from today, return all future/active deadlines
    if not deadlines:
        deadlines = query.filter(Deadline.status != "graded").order_by(Deadline.due_date.asc()).limit(10).all()

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
        "deadlines": results,
        "citations": citations
    }

# Tool 6: Academic Tasks
def get_academic_tasks(
    db: Session,
    status: Optional[str] = None,
    module_code: Optional[str] = None
) -> Dict[str, Any]:
    _log_tool_call("get_academic_tasks", {"status": status, "module_code": module_code})
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

# Tool 7: Timetable / Calendar Events
def get_university_timetable(
    db: Session,
    target_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    module_code: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    _log_tool_call("get_university_timetable", {"target_date": target_date, "start_date": start_date, "end_date": end_date, "module_code": module_code})
    query = db.query(TimetableEvent)
    if target_date:
        query = query.filter(TimetableEvent.start_time.startswith(target_date))
    elif start_date or end_date:
        if start_date:
            query = query.filter(TimetableEvent.start_time >= start_date)
        if end_date:
            query = query.filter(TimetableEvent.start_time <= end_date)
    else:
        # Fetch all upcoming or recent events
        query = query.order_by(TimetableEvent.start_time.asc())

    if module_code:
        query = query.filter(func.lower(TimetableEvent.module_code) == module_code.lower())

    events = query.limit(limit).all()
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

# Tool 8: Daily Summaries
def get_daily_summaries(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 7
) -> Dict[str, Any]:
    _log_tool_call("get_daily_summaries", {"start_date": start_date, "end_date": end_date})
    query = db.query(DailySummary)
    if start_date:
        query = query.filter(DailySummary.date >= start_date)
    if end_date:
        query = query.filter(DailySummary.date <= end_date)

    summaries = query.order_by(DailySummary.date.desc()).limit(limit).all()
    results = [s.to_dict() for s in summaries]
    citations = []
    for s in summaries:
        citations.append({
            "type": "daily_summary",
            "id": f"summary-{s.date}",
            "title": f"Daily Summary ({s.date})",
            "snippet": s.summary[:140],
            "date": s.date
        })

    return {
        "count": len(results),
        "summaries": results,
        "citations": citations
    }

# Tool 9: Linked Photos (Immich / Photo Pipeline Scaffold)
def get_linked_photos(
    db: Session,
    date_str: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    _log_tool_call("get_linked_photos", {"date_str": date_str})
    query = db.query(PhotoEvent)
    if date_str:
        query = query.filter(PhotoEvent.date == date_str)
    photos = query.order_by(PhotoEvent.timestamp.desc()).limit(limit).all()
    return {
        "count": len(photos),
        "photos": [p.to_dict() for p in photos],
        "citations": []
    }

# Write Tool 1: Add Journal Entry
def add_journal_entry(
    db: Session,
    date_str: str,
    raw_text: str,
    mood: Optional[str] = "Neutral"
) -> Dict[str, Any]:
    _log_tool_call("add_journal_entry", {"date": date_str, "raw_text": raw_text[:50], "mood": mood}, is_write=True)
    entry = JournalEntry(
        date=date_str,
        raw_text=raw_text,
        mood=mood or "Neutral",
        summary=raw_text[:120],
        tags_json=json.dumps(["logged"]),
        people_json=json.dumps([]),
        nutrition_json=json.dumps({})
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "success": True,
        "id": entry.id,
        "date": entry.date,
        "message": f"Successfully logged journal entry for {date_str}."
    }

# Write Tool 2: Schedule Reminder
def schedule_reminder(
    db: Session,
    title: str,
    due_at: str,
    notes: Optional[str] = ""
) -> Dict[str, Any]:
    _log_tool_call("schedule_reminder", {"title": title, "due_at": due_at, "notes": notes}, is_write=True)
    rem = Reminder(
        title=title,
        due_at=due_at,
        notes=notes or "",
        status="pending"
    )
    db.add(rem)
    db.commit()
    db.refresh(rem)
    return {
        "success": True,
        "id": rem.id,
        "title": rem.title,
        "due_at": rem.due_at,
        "message": f"Successfully scheduled reminder '{title}' for {due_at}."
    }

TOOL_DEFINITIONS = [
    {
        "name": "query_journal",
        "description": "Searches daily journal entries by date range, specific date, or keyword.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD start date"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD end date"},
                "target_date": {"type": "string", "description": "Specific date YYYY-MM-DD"},
                "keyword": {"type": "string", "description": "Topic, activity, or keyword to match"},
                "limit": {"type": "integer", "description": "Max entries (default 10)"}
            }
        }
    },
    {
        "name": "get_person_dossier",
        "description": "Retrieves contact info, learned personal facts/preferences, and interaction history for an individual.",
        "parameters": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string", "description": "First or full name of the person (e.g. Sam, Alex)"}
            },
            "required": ["person_name"]
        }
    },
    {
        "name": "get_garmin_metrics",
        "description": "Fetches physical telemetry (steps, active/resting calories, sleep duration/score, resting HR) with precomputed aggregates (min, max, avg, totals).",
        "parameters": {
            "type": "object",
            "properties": {
                "target_date": {"type": "string", "description": "Specific date YYYY-MM-DD"},
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD"}
            }
        }
    },
    {
        "name": "get_nutrition_summary",
        "description": "Fetches dietary intake, total calories, and macronutrient breakdown (protein, carbs, fat) with computed totals for a date or date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_date": {"type": "string", "description": "Specific date YYYY-MM-DD"},
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD"}
            }
        }
    },
    {
        "name": "get_upcoming_deadlines",
        "description": "Retrieves upcoming university coursework, assignments, and exam deadlines with percentage weightings.",
        "parameters": {
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "description": "Days forward to check (default 14)"},
                "module_code": {"type": "string", "description": "Optional module code e.g. COMP2181"},
                "reference_date": {"type": "string", "description": "Anchor date YYYY-MM-DD"}
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
        "name": "get_university_timetable",
        "description": "Fetches university lecture timetable, tutorials, drop-ins, and classroom schedule with locations and rooms.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_date": {"type": "string", "description": "Specific date YYYY-MM-DD"},
                "start_date": {"type": "string", "description": "Start ISO date"},
                "end_date": {"type": "string", "description": "End ISO date"},
                "module_code": {"type": "string", "description": "Optional module code"},
                "limit": {"type": "integer", "description": "Max events"}
            }
        }
    },
    {
        "name": "get_daily_summaries",
        "description": "Fetches daily executive rollups covering health, nutrition, and personal highlights.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                "limit": {"type": "integer", "description": "Max summaries"}
            }
        }
    },
    {
        "name": "get_linked_photos",
        "description": "Retrieves photo metadata and thumbnails linked to dates or locations.",
        "parameters": {
            "type": "object",
            "properties": {
                "date_str": {"type": "string", "description": "YYYY-MM-DD date"}
            }
        }
    },
    {
        "name": "add_journal_entry",
        "description": "Logs a new daily journal entry.",
        "parameters": {
            "type": "object",
            "properties": {
                "date_str": {"type": "string", "description": "YYYY-MM-DD date"},
                "raw_text": {"type": "string", "description": "Journal entry text"},
                "mood": {"type": "string", "description": "Mood descriptor"}
            },
            "required": ["date_str", "raw_text"]
        }
    },
    {
        "name": "schedule_reminder",
        "description": "Schedules a reminder for a future time.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Reminder title/task"},
                "due_at": {"type": "string", "description": "Target timestamp e.g. 2026-10-15T09:00:00"},
                "notes": {"type": "string", "description": "Optional extra details"}
            },
            "required": ["title", "due_at"]
        }
    }
]
