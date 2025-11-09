"""
Logging middleware for request sanitization.
"""
import logging
from fastapi import Request

from ...security import sanitize_log

logger = logging.getLogger(__name__)


async def sanitize_logs_middleware(request: Request, call_next):
    """Ensure no PII is logged."""
    # Log sanitized request info
    sanitized_path = sanitize_log(request.url.path)
    logger.info(f"Request: {request.method} {sanitized_path}")
    
    response = await call_next(request)
    return response


__all__ = ["sanitize_logs_middleware"]