import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.timetable_service import timetable_service

logger = logging.getLogger("seed")

router = APIRouter(prefix="/api", tags=["system"])

@router.post("/system/resync")
@router.post("/seed")
async def resync_real_data(db: Session = Depends(get_db)):
    """
    Resynchronizes actual user data:
    1. Durham University MyTimetable & Blackboard iCal feeds
    2. MongoDB cluster historical items
    """
    logger.info("Resyncing actual user data...")
    ical_res = timetable_service.sync_ical_feeds(db)
    mongo_res = timetable_service.sync_from_mongodb(db)
    status = timetable_service.get_status(db)

    return {
        "status": "success",
        "success": True,
        "message": "Real university feeds & database synchronized successfully.",
        "ical_sync": ical_res,
        "mongo_sync": mongo_res,
        "timetable_status": status
    }
