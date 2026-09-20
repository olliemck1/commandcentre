import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .routes import (
    metrics_router, 
    journal_router, 
    crm_router, 
    university_router, 
    chat_router, 
    seed_router
)
from .services import scheduler_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

# Initialize database tables on import
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Start scheduler
    logger.info("Starting background scheduler...")
    scheduler_service.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down background scheduler...")
    scheduler_service.shutdown()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Full-stack Command Centre API consolidating Garmin physical activities, daily journaling with structured LLM nutrition/social extraction, and personal CRM graph.",
    lifespan=lifespan
)

# Enable CORS for local Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(metrics_router)
app.include_router(journal_router)
app.include_router(crm_router)
app.include_router(university_router)
app.include_router(chat_router)
app.include_router(seed_router)

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "docs": "/docs"
    }

@app.get("/api/health")
def health():
    return {"status": "healthy"}
