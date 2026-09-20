from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.crm import Interaction
from ..schemas.crm import (
    PersonSummaryResponse,
    PersonDetailResponse,
    PersonUpdate,
    InteractionResponse
)
from ..services.crm_service import crm_service

router = APIRouter(prefix="/api", tags=["crm"])

@router.get("/people", response_model=List[PersonSummaryResponse])
def list_people(
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return crm_service.get_people(db, search=search, tag=tag)

@router.get("/people/{person_id}", response_model=PersonDetailResponse)
def get_person(person_id: int, db: Session = Depends(get_db)):
    detail = crm_service.get_person_detail(db, person_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Person not found")
    return detail

@router.put("/people/{person_id}", response_model=PersonDetailResponse)
def update_person(
    person_id: int,
    req: PersonUpdate,
    db: Session = Depends(get_db)
):
    updated = crm_service.update_person(db, person_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail="Person not found")
    return updated

@router.delete("/people/{person_id}")
def delete_person(person_id: int, db: Session = Depends(get_db)):
    success = crm_service.delete_person(db, person_id)
    if not success:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Person deleted successfully"}

@router.get("/interactions", response_model=List[InteractionResponse])
def list_recent_interactions(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db)
):
    interactions = db.query(Interaction).order_by(Interaction.date.desc(), Interaction.created_at.desc()).limit(limit).all()
    return [i.to_dict() for i in interactions]
