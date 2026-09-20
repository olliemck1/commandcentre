from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.daily_metrics import DailyMetrics
from ..schemas.metrics import DailyMetricsResponse, GarminStatusResponse, GarminSyncRequest
from ..services.garmin_service import garmin_service

router = APIRouter(prefix="/api", tags=["metrics"])

@router.get("/metrics/{target_date}", response_model=DailyMetricsResponse)
def get_daily_metrics(target_date: str, db: Session = Depends(get_db)):
    metric = db.query(DailyMetrics).filter(DailyMetrics.date == target_date).first()
    if not metric:
        # Auto-sync/generate on first view of a date
        metric = garmin_service.sync_date(db, target_date)
    return metric.to_dict()

@router.post("/garmin/sync", response_model=DailyMetricsResponse)
def sync_garmin(
    req: Optional[GarminSyncRequest] = None,
    target_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    chosen_date = (req.date if req and req.date else None) or target_date or date.today().isoformat()
    force_demo = req.force_demo if req and req.force_demo is not None else False
    metric = garmin_service.sync_date(db, chosen_date, force_demo=force_demo)
    return metric.to_dict()

@router.get("/garmin/status", response_model=GarminStatusResponse)
def get_garmin_status():
    return garmin_service.get_status()

@router.get("/llm/status")
async def get_llm_status():
    from ..config import settings
    import httpx
    has_key = bool(settings.GEMINI_API_KEY)
    valid = False
    error_msg = None
    model = settings.GEMINI_MODEL or "gemini-3.6-flash"

    if has_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": "ping"}]}]}
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    valid = True
                else:
                    error_msg = f"HTTP {res.status_code}: {res.text[:100]}"
        except Exception as ex:
            error_msg = str(ex)

    return {
        "configured": has_key,
        "valid": valid,
        "provider": "gemini" if has_key else "heuristic",
        "model": model,
        "error": error_msg
    }

