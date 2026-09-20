from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class PersonBase(BaseModel):
    name: str
    aliases: List[str] = []
    first_met_date: Optional[str] = None
    notes_summary: str = ""
    tags: List[str] = []

class PersonCreate(PersonBase):
    pass

class PersonUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    first_met_date: Optional[str] = None
    notes_summary: Optional[str] = None
    tags: Optional[List[str]] = None

class InteractionResponse(BaseModel):
    id: int
    person_id: int
    person_name: Optional[str] = None
    journal_entry_id: Optional[int] = None
    date: str
    context_snippet: str
    sentiment: str
    location: Optional[str] = None
    extracted_facts: List[str] = []
    created_at: Optional[str] = None

class PersonSummaryResponse(BaseModel):
    id: int
    name: str
    slug: str
    aliases: List[str] = []
    first_met_date: Optional[str] = None
    last_seen_date: Optional[str] = None
    interaction_count: int = 0
    notes_summary: str = ""
    tags: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class PersonDetailResponse(PersonSummaryResponse):
    interactions: List[InteractionResponse] = []
