"""
API package for FastAPI application and routers.
"""

from .main import create_app, app

__all__ = [
    "create_app",
    "app",
]