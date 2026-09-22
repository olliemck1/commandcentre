import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .routes import (
    metrics_router, 
    journal_router, 
    crm_router, 
    university_router, 
    chat_router, 
    seed_router,
    auth_router
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

# Enable CORS for local Vite development and cloud frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Middleware: Enforce access passcode on all API routes when APP_ACCESS_TOKEN is set
@app.middleware("http")
async def verify_access_token(request: Request, call_next):
    # 1. Always allow CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # 2. Public paths that never require authentication
    public_paths = [
        "/", 
        "/docs", 
        "/openapi.json", 
        "/api/health", 
        "/api/auth/status", 
        "/api/auth/verify"
    ]
    if request.url.path in public_paths:
        return await call_next(request)
    
    # 3. If APP_ACCESS_TOKEN is configured, verify the Bearer or X-Access-Token header
    if settings.APP_ACCESS_TOKEN:
        auth_header = request.headers.get("Authorization") or ""
        x_token = request.headers.get("X-Access-Token") or ""
        
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif x_token:
            token = x_token.strip()
            
        if not token or token != settings.APP_ACCESS_TOKEN:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Invalid or missing access token"}
            )
            
    return await call_next(request)

# Register routes
app.include_router(auth_router)
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
