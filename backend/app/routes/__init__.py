from .metrics import router as metrics_router
from .journal import router as journal_router
from .crm import router as crm_router
from .university import router as university_router
from .chat import router as chat_router
from .seed import router as seed_router

__all__ = [
    "metrics_router", 
    "journal_router", 
    "crm_router", 
    "university_router", 
    "chat_router", 
    "seed_router"
]
