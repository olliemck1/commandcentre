from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional
from ..config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

class VerifyRequest(BaseModel):
    token: str

@router.get("/status")
def get_auth_status():
    """Returns whether authentication is required on this deployment."""
    return {
        "auth_required": bool(settings.APP_ACCESS_TOKEN)
    }

@router.post("/verify")
def verify_token(req: VerifyRequest):
    """Verifies a passcode against the configured APP_ACCESS_TOKEN."""
    if not settings.APP_ACCESS_TOKEN:
        # If no access token is configured, all requests are permitted
        return {"valid": True, "auth_required": False}

    if req.token == settings.APP_ACCESS_TOKEN:
        return {"valid": True, "auth_required": True}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid access passcode"
    )
