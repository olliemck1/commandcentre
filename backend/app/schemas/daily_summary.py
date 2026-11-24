"""Schemas for Nightly Rollup and Daily Summary generation."""
from typing import List, Optional
from pydantic import BaseModel, Field

class DailyRollupIntelligence(BaseModel):
    summary: str = Field(description="Crisp 2-3 sentence executive synthesis of the day's achievements, routines, and overall focus.")
    mood: str = Field(description="Dominant mood or cognitive state (e.g. Focused, Exhausted, Grounded, High Energy, Social).")
    health_summary: str = Field(description="Summary of physical strain and recovery: steps, sleep duration, sleep score, active calories, resting HR.")
    nutrition_summary: str = Field(description="Summary of nutritional intake: total calories, protein/carbs/fat, key meals.")
    key_themes: List[str] = Field(default_factory=list, description="3-5 thematic tags for the day.")

class ContextUpdateItem(BaseModel):
    key: str = Field(description="Target context key: e.g. 'active_projects', 'training_routine', 'recurring_people', 'preferences'")
    facts_to_add: List[str] = Field(default_factory=list, description="New enduring facts or updates to merge into this category.")
    facts_to_retire: List[str] = Field(default_factory=list, description="Obsolete facts to remove if explicitly superseded.")

class ContextMergeIntelligence(BaseModel):
    updates: List[ContextUpdateItem] = Field(default_factory=list, description="List of incremental merges across context keys.")
