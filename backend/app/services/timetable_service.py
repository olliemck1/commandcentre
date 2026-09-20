import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta, timezone
import httpx
from icalendar import Calendar
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..config import settings
from ..models.university import Module, Deadline, TimetableEvent

logger = logging.getLogger("timetable_service")

# Palette of colors for auto-provisioned modules
MODULE_COLORS = [
    "#6366f1", # Indigo
    "#3b82f6", # Blue
    "#0ea5e9", # Sky
    "#10b981", # Emerald
    "#8b5cf6", # Violet
    "#ec4899", # Pink
    "#f59e0b", # Amber
    "#14b8a6", # Teal
    "#f97316", # Orange
]

def extract_module_info(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extracts module code (e.g. COMP2221) and optional module title from event text.
    Format examples:
      'COMP2221: Programming Paradigms - Lecture' -> ('COMP2221', 'Programming Paradigms')
      'MATH2731: Computational Mathematics II - Drop-In Class' -> ('MATH2731', 'Computational Mathematics II')
    """
    if not text:
        return None, None
    
    # Check for 'CODE: Title - Type'
    m = re.match(r'([A-Z]{4}\d{4}):\s*([^-]+)', text)
    if m:
        return m.group(1).upper().strip(), m.group(2).strip()
    
    # Generic module code match
    m2 = re.search(r'\b([A-Z]{4}\d{4})\b', text)
    if m2:
        return m2.group(1).upper().strip(), None
        
    return None, None

def determine_event_type(title: str, description: str = "") -> str:
    combined = f"{title} {description}".lower()
    if "lecture" in combined:
        return "lecture"
    elif "drop-in" in combined or "drop in" in combined:
        return "drop-in"
    elif "tutorial" in combined:
        return "tutorial"
    elif "practical" in combined or "lab" in combined:
        return "practical"
    elif "office hour" in combined or "office-hour" in combined:
        return "office-hours"
    elif "exam" in combined or "test" in combined:
        return "exam"
    elif "seminar" in combined:
        return "seminar"
    elif "coursework" in combined or "assignment" in combined or "submission" in combined:
        return "deadline"
    elif "talk" in combined or "induction" in combined or "meeting" in combined:
        return "event"
    return "class"

def ensure_module(db: Session, code: str, title: Optional[str] = None) -> Module:
    """Gets an existing module or provisions a new one."""
    code_clean = code.upper().strip()
    module = db.query(Module).filter(Module.code == code_clean).first()
    if module:
        if title and (not module.title or module.title.startswith("Module ")):
            module.title = title
            db.commit()
        return module
    
    # Assign color deterministically based on hash
    color_index = abs(hash(code_clean)) % len(MODULE_COLORS)
    mod_color = MODULE_COLORS[color_index]
    mod_title = title if title else f"Module {code_clean}"
    
    new_mod = Module(
        code=code_clean,
        title=mod_title,
        term="2026/2027",
        credits=20,
        color=mod_color,
        description=f"Auto-imported from university timetable for {code_clean}."
    )
    db.add(new_mod)
    db.commit()
    db.refresh(new_mod)
    return new_mod

def parse_datetime_field(dt_field) -> Optional[str]:
    """Converts icalendar date/datetime or standard datetime to ISO string."""
    if not dt_field:
        return None
    
    # If it has .dt attribute (icalendar component)
    val = getattr(dt_field, "dt", dt_field)
    
    if isinstance(val, datetime):
        return val.isoformat()
    elif isinstance(val, date):
        # Date only: midnight ISO
        return datetime(val.year, val.month, val.day).isoformat()
    elif isinstance(val, str):
        return val
    return None

class TimetableService:
    def ensure_module(self, db: Session, code: str, title: Optional[str] = None) -> Module:
        return ensure_module(db, code, title)

    def sync_ical_feeds(
        self,
        db: Session,
        sources: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Synchronizes timetable events from live iCal feeds.
        Default sources are Durham MyTimetable and Durham Blackboard.
        """
        if sources is None:
            sources = []
            if settings.MYTIMETABLE_ICAL_URL:
                sources.append({"url": settings.MYTIMETABLE_ICAL_URL, "name": "mytimetable"})
            if settings.BLACKBOARD_ICAL_URL:
                sources.append({"url": settings.BLACKBOARD_ICAL_URL, "name": "blackboard"})

        total_processed = 0
        new_count = 0
        updated_count = 0
        modules_provisioned = set()
        errors = []

        for src in sources:
            url = src.get("url")
            source_name = src.get("name", "ical")
            if not url:
                continue

            try:
                logger.info(f"Fetching iCal feed from {url} ({source_name})...")
                res = httpx.get(url, timeout=20.0, follow_redirects=True)
                if res.status_code != 200:
                    errors.append(f"HTTP {res.status_code} for {source_name}")
                    continue

                cal = Calendar.from_ical(res.text)
                for item in cal.walk("VEVENT"):
                    uid = str(item.get("uid") or "")
                    if not uid:
                        continue

                    summary = str(item.get("summary") or "Untitled Event")
                    description = str(item.get("description") or "")
                    location = str(item.get("location") or "")
                    
                    dtstart = parse_datetime_field(item.get("dtstart"))
                    dtend = parse_datetime_field(item.get("dtend"))

                    if not dtstart:
                        continue

                    # If end time missing, default to 1 hour after start
                    if not dtend:
                        try:
                            start_dt = datetime.fromisoformat(dtstart)
                            dtend = (start_dt + timedelta(hours=1)).isoformat()
                        except Exception:
                            dtend = dtstart

                    # Extract module
                    mod_code, mod_title = extract_module_info(summary)
                    module_id = None
                    if mod_code:
                        mod = ensure_module(db, mod_code, mod_title)
                        module_id = mod.id
                        modules_provisioned.add(mod_code)

                    ev_type = determine_event_type(summary, description)

                    # Upsert event
                    existing = db.query(TimetableEvent).filter(TimetableEvent.sync_id == uid).first()
                    if existing:
                        existing.title = summary
                        existing.subject = location or (mod_code or "University")
                        existing.location = location
                        existing.start_time = dtstart
                        existing.end_time = dtend
                        existing.event_type = ev_type
                        existing.module_code = mod_code
                        existing.module_id = module_id
                        existing.description = description
                        existing.source = source_name
                        updated_count += 1
                    else:
                        new_ev = TimetableEvent(
                            sync_id=uid,
                            source=source_name,
                            title=summary,
                            subject=location or (mod_code or "University"),
                            location=location,
                            start_time=dtstart,
                            end_time=dtend,
                            event_type=ev_type,
                            module_code=mod_code,
                            module_id=module_id,
                            description=description,
                            status="scheduled"
                        )
                        db.add(new_ev)
                        new_count += 1

                    total_processed += 1

                db.commit()
                logger.info(f"Successfully processed {source_name}: {new_count} new, {updated_count} updated.")

            except Exception as ex:
                logger.error(f"Error syncing {source_name}: {ex}", exc_info=True)
                errors.append(f"{source_name}: {str(ex)}")

        return {
            "success": len(errors) == 0,
            "source": "ical_feeds",
            "total_processed": total_processed,
            "new_events": new_count,
            "updated_events": updated_count,
            "modules_provisioned": sorted(list(modules_provisioned)),
            "message": f"Processed {total_processed} events ({new_count} new, {updated_count} updated). Errors: {errors}" if errors else f"Successfully synced {total_processed} timetable events."
        }

    def sync_from_mongodb(
        self,
        db: Session,
        mongo_uri: Optional[str] = None,
        db_name: str = "test"
    ) -> Dict[str, Any]:
        """
        Imports assignments, timetable events, and modules from existing MongoDB cluster.
        """
        import pymongo

        uri = mongo_uri or settings.MONGODB_URI
        if not uri:
            return {
                "success": False,
                "source": "mongodb",
                "total_processed": 0,
                "new_events": 0,
                "updated_events": 0,
                "modules_provisioned": [],
                "message": "No MongoDB connection string provided in settings."
            }

        total_processed = 0
        new_count = 0
        updated_count = 0
        modules_provisioned = set()

        try:
            logger.info("Connecting to MongoDB cluster...")
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
            mongo_db = client[db_name]
            assignments_col = mongo_db["assignments"]

            cursor = assignments_col.find({})
            for doc in cursor:
                sync_id = str(doc.get("syncId") or doc.get("_id"))
                title = doc.get("title", "Untitled Event")
                subject = doc.get("subject", "")
                source = doc.get("source", "mongodb")
                
                # Dates
                start_dt = doc.get("startDate") or doc.get("dueDate")
                end_dt = doc.get("endDate") or doc.get("dueDate")
                
                start_iso = start_dt.isoformat() if isinstance(start_dt, (datetime, date)) else str(start_dt or "")
                end_iso = end_dt.isoformat() if isinstance(end_dt, (datetime, date)) else str(end_dt or start_iso)

                if not start_iso:
                    continue

                mod_code, mod_title = extract_module_info(title)
                if not mod_code and subject:
                    mod_code, _ = extract_module_info(subject)

                module_id = None
                if mod_code:
                    mod = ensure_module(db, mod_code, mod_title)
                    module_id = mod.id
                    modules_provisioned.add(mod_code)

                ev_type = determine_event_type(title, subject)

                # Upsert into TimetableEvent
                existing = db.query(TimetableEvent).filter(TimetableEvent.sync_id == sync_id).first()
                if existing:
                    existing.title = title
                    existing.subject = subject
                    existing.location = subject
                    existing.start_time = start_iso
                    existing.end_time = end_iso
                    existing.event_type = ev_type
                    existing.module_code = mod_code
                    existing.module_id = module_id
                    existing.source = source
                    updated_count += 1
                else:
                    new_ev = TimetableEvent(
                        sync_id=sync_id,
                        source=source,
                        title=title,
                        subject=subject,
                        location=subject,
                        start_time=start_iso,
                        end_time=end_iso,
                        event_type=ev_type,
                        module_code=mod_code,
                        module_id=module_id,
                        description=f"Imported from MongoDB (source: {source})",
                        status="scheduled"
                    )
                    db.add(new_ev)
                    new_count += 1

                # If the item has priority / status and looks like an assignment/deadline, also sync into Deadline table if not there
                if (source == "blackboard" or "assignment" in title.lower() or "coursework" in title.lower()) and module_id:
                    due_date_str = start_iso[:10]
                    existing_deadline = db.query(Deadline).filter(
                        Deadline.module_id == module_id,
                        Deadline.title == title
                    ).first()
                    if not existing_deadline:
                        db.add(Deadline(
                            module_id=module_id,
                            title=title,
                            due_date=due_date_str,
                            priority=doc.get("priority", "Medium"),
                            status="pending" if doc.get("status") != "Completed" else "submitted",
                            resource_link=str(doc.get("resourceLink", "")).strip()
                        ))

                total_processed += 1

            db.commit()
            client.close()

            return {
                "success": True,
                "source": "mongodb",
                "total_processed": total_processed,
                "new_events": new_count,
                "updated_events": updated_count,
                "modules_provisioned": sorted(list(modules_provisioned)),
                "message": f"Successfully imported {total_processed} items from MongoDB ({new_count} new, {updated_count} updated)."
            }

        except Exception as ex:
            logger.error(f"MongoDB sync error: {ex}", exc_info=True)
            return {
                "success": False,
                "source": "mongodb",
                "total_processed": total_processed,
                "new_events": new_count,
                "updated_events": updated_count,
                "modules_provisioned": sorted(list(modules_provisioned)),
                "message": f"MongoDB import failed: {str(ex)}"
            }

    def get_events(
        self,
        db: Session,
        target_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        module_code: Optional[str] = None,
        source: Optional[str] = None,
        upcoming_only: bool = False,
        limit: int = 100
    ) -> List[TimetableEvent]:
        query = db.query(TimetableEvent)

        if target_date:
            # Match date prefix YYYY-MM-DD
            query = query.filter(TimetableEvent.start_time.startswith(target_date))
        elif start_date or end_date:
            if start_date:
                query = query.filter(TimetableEvent.start_time >= start_date)
            if end_date:
                query = query.filter(TimetableEvent.start_time <= end_date)
        elif upcoming_only:
            now_iso = datetime.utcnow().isoformat()
            query = query.filter(TimetableEvent.start_time >= now_iso)

        if module_code:
            query = query.filter(func.lower(TimetableEvent.module_code) == module_code.lower())

        if source:
            query = query.filter(TimetableEvent.source == source)

        return query.order_by(TimetableEvent.start_time.asc()).limit(limit).all()

    def get_status(self, db: Session) -> Dict[str, Any]:
        total_count = db.query(TimetableEvent).count()
        sources = db.query(TimetableEvent.source, func.count(TimetableEvent.id)).group_by(TimetableEvent.source).all()
        modules_count = db.query(func.count(func.distinct(TimetableEvent.module_code))).scalar()
        
        now_iso = datetime.utcnow().isoformat()
        upcoming_count = db.query(TimetableEvent).filter(TimetableEvent.start_time >= now_iso).count()

        return {
            "total_events": total_count,
            "upcoming_events": upcoming_count,
            "distinct_modules": modules_count,
            "by_source": {s: count for s, count in sources}
        }

timetable_service = TimetableService()
