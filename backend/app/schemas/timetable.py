from typing import Optional, List
from pydantic import BaseModel

class TimetableEventResponse(BaseModel):
    id: int
    sync_id: str
    source: str
    title: str
    subject: Optional[str] = None
    location: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    event_type: str
    module_code: Optional[str] = None
    module_id: Optional[int] = None
    module_color: Optional[str] = None
    module_title: Optional[str] = None
    description: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    _id: Optional[str] = None
    syncId: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    dueDate: Optional[str] = None
    priority: Optional[str] = "Medium"
    resourceLink: Optional[str] = ""

class TimetableUpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    subject: Optional[str] = None
    location: Optional[str] = None
    resourceLink: Optional[str] = None

class TimetableCreateRequest(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = ""
    subject: Optional[str] = ""
    module_code: Optional[str] = None
    event_type: Optional[str] = "lecture"
    description: Optional[str] = ""

class TimetableSyncRequest(BaseModel):
    ical_url: Optional[str] = None
    source_name: Optional[str] = None
    mongodb_uri: Optional[str] = None

class TimetableSyncResponse(BaseModel):
    success: bool
    source: str
    total_processed: int
    new_events: int
    updated_events: int
    modules_provisioned: List[str] = []
    message: str
