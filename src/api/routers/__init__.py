"""
API routers package.
"""

from .redaction import router as redaction_router
from .health import router as health_router
from .metrics import router as metrics_router
from .policy import router as policy_router
from .streaming import router as streaming_router

__all__ = [
    "redaction_router",
    "health_router", 
    "metrics_router",
    "policy_router",
    "streaming_router",
]