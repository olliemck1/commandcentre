from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class NutritionItem(BaseModel):
    name: str
    portion: str = "1 serving"
    calories: int = 0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0

class NutritionSummary(BaseModel):
    items: List[NutritionItem] = []
    total_calories: int = 0
    total_protein_g: float = 0.0
    total_carbs_g: float = 0.0
    total_fat_g: float = 0.0
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)

class ExtractedPerson(BaseModel):
    name: str
    context: str = "" # e.g. "Coffee at Blue Bottle discussing product launch"
    sentiment: str = "neutral" # positive, neutral, negative
    facts_learned: List[str] = [] # e.g. ["Likes flat whites with oat milk", "Promoted to VP"]
    location: Optional[str] = None

class ExtractedJournalIntelligence(BaseModel):
    nutrition: NutritionSummary = Field(default_factory=NutritionSummary)
    people: List[ExtractedPerson] = Field(default_factory=list)
    summary: str = ""
    mood_tag: str = "Neutral"
    tags: List[str] = Field(default_factory=list)

class JournalCreateRequest(BaseModel):
    date: str # YYYY-MM-DD
    raw_text: str

class JournalEntryResponse(BaseModel):
    id: int
    date: str
    raw_text: str
    summary: str
    mood: str
    nutrition: Dict[str, Any]
    people: List[Dict[str, Any]]
    tags: List[str]
    created_at: Optional[str] = None
