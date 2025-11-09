"""
Middleware package for the data redaction gateway.
"""

from .proxy import ProxyMiddleware

__all__ = [
    "ProxyMiddleware"
]