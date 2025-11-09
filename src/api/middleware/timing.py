"""
Timing middleware for request processing time tracking.
"""
import time
import logging
from fastapi import Request

from ...policy import get_policy_loader

logger = logging.getLogger(__name__)


async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # Convert to ms
    response.headers["X-Process-Time-Ms"] = str(process_time)
    
    # Add policy headers
    policy_loader = get_policy_loader()
    response.headers["X-Redaction-Policy"] = "PII-PCI-Redaction"
    response.headers["X-Policy-Version"] = policy_loader.get_policy_version()
    
    return response


__all__ = ["add_process_time_header"]