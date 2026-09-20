import json
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.journal import JournalEntry
from ..schemas.journal import JournalCreateRequest, JournalEntryResponse
from ..services.llm_service import llm_service
from ..services.crm_service import crm_service

from ..models.nutrition import NutritionLog

logger = logging.getLogger("journal_routes")
router = APIRouter(prefix="/api/journal", tags=["journal"])

@router.post("", response_model=JournalEntryResponse)
async def create_journal_entry(
    req: JournalCreateRequest,
    db: Session = Depends(get_db)
):
    if not req.raw_text.strip():
        raise HTTPException(status_code=400, detail="Journal entry text cannot be empty")

    # 1. Extract intelligence via LLM service
    intelligence = await llm_service.extract_journal_intelligence(req.raw_text, req.date)

    # 2. Store Journal Entry
    entry = JournalEntry(
        date=req.date,
        raw_text=req.raw_text,
        summary=intelligence.summary,
        mood=intelligence.mood_tag,
        nutrition_json=json.dumps(intelligence.nutrition.model_dump()),
        people_json=json.dumps([p.model_dump() for p in intelligence.people]),
        tags_json=json.dumps(intelligence.tags)
    )
    db.add(entry)
    db.flush()

    # 2b. Store individual NutritionLog items
    for item in intelligence.nutrition.items:
        nut_log = NutritionLog(
            date=req.date,
            journal_entry_id=entry.id,
            item_name=item.name,
            portion=item.portion,
            estimated_calories=item.calories,
            protein=item.protein_g,
            carbs=item.carbs_g,
            fat=item.fat_g,
            confidence=intelligence.nutrition.confidence,
            created_at=datetime.utcnow()
        )
        db.add(nut_log)

    # 3. Process CRM entities & interactions
    crm_service.process_extracted_people(
        db=db,
        people=intelligence.people,
        journal_entry=entry,
        date_str=req.date
    )

    db.commit()
    db.refresh(entry)
    return entry.to_dict()

@router.get("/nutrition/{target_date}")
def get_nutrition_logs_for_date(target_date: str, db: Session = Depends(get_db)):
    logs = db.query(NutritionLog).filter(NutritionLog.date == target_date).all()
    return [l.to_dict() for l in logs]

@router.get("/{target_date}", response_model=List[JournalEntryResponse])
def get_journal_entries_for_date(
    target_date: str,
    db: Session = Depends(get_db)
):
    entries = db.query(JournalEntry).filter(JournalEntry.date == target_date).order_by(JournalEntry.created_at.desc()).all()
    return [e.to_dict() for e in entries]

@router.get("", response_model=List[JournalEntryResponse])
def get_recent_journal_entries(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    entries = db.query(JournalEntry).order_by(JournalEntry.date.desc(), JournalEntry.created_at.desc()).limit(limit).all()
    return [e.to_dict() for e in entries]

@router.delete("/{entry_id}")
def delete_journal_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Journal entry deleted successfully"}
