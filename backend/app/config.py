import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "Personal Command Centre"
    DATABASE_URL: str = Field(default="sqlite:///./command_centre.db")
    
    # Garmin credentials
    GARMIN_EMAIL: str = Field(default="")
    GARMIN_PASSWORD: str = Field(default="")
    GARMIN_TOKENS_DIR: str = Field(default=str(Path(__file__).resolve().parent.parent / ".garmin_tokens"))
    
    # LLM Settings
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash")
    # Tried in order when primary model returns 429/503
    GEMINI_FALLBACK_MODELS: list = Field(default=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"])
    OPENAI_API_KEY: str = Field(default="")
    LLM_PROVIDER: str = Field(default="auto") # 'gemini', 'openai', or 'mock'
    
    # Security / Single-user Access Passcode (locks all API routes when set)
    APP_ACCESS_TOKEN: str = Field(default="")
    
    # Scheduler
    SYNC_ENABLED: bool = Field(default=True)
    SYNC_HOUR: int = Field(default=23)
    SYNC_MINUTE: int = Field(default=30)

    # University Timetable & Academic Feeds (Configured via .env or cloud environment variables)
    MONGODB_URI: str = Field(default="")
    MYTIMETABLE_ICAL_URL: str = Field(default="")
    BLACKBOARD_ICAL_URL: str = Field(default="")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
