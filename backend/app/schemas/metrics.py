from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ActivityItem(BaseModel):
    id: Optional[str] = None
    name: str
    type: str # running, cycling, walking, swimming, strength, etc.
    duration_mins: float
    distance_km: Optional[float] = 0.0
    calories: Optional[int] = 0
    avg_hr: Optional[int] = None
    start_time: Optional[str] = None

class DailyMetricsResponse(BaseModel):
    id: Optional[int] = None
    date: str
    steps: int = 0
    step_goal: int = 10000
    active_calories: int = 0
    resting_calories: int = 0
    total_calories_burned: int = 0
    distance_meters: float = 0.0
    resting_heart_rate: Optional[int] = None
    sleep_seconds: int = 0
    sleep_score: Optional[int] = None
    activities: List[Dict[str, Any]] = []
    synced_at: Optional[str] = None

class GarminSyncRequest(BaseModel):
    date: Optional[str] = None # YYYY-MM-DD, defaults to today
    force_demo: Optional[bool] = False

class GarminStatusResponse(BaseModel):
    connected: bool
    configured: bool
    email: Optional[str] = None
    last_sync: Optional[str] = None
    session_valid: bool
    mode: str # 'live' or 'demo'
    message: Optional[str] = None
