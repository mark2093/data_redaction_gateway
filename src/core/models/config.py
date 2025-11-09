"""
Configuration-related models.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import Field

from .base import BaseModel
from .redaction import RedactionRule


class PolicyConfig(BaseModel):
    """Policy configuration from YAML."""
    version: str = Field(..., description="Policy version")
    effective_date: Optional[str] = Field(None)
    rules: List[RedactionRule] = Field(..., description="List of redaction rules")
    
    class Config:
        extra = "allow"


class StreamDataPoint(BaseModel):
    """Model for simulated stream data point."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_type: str = Field(..., description="Type of data (order, transaction, chat)")
    payload: Dict[str, Any] = Field(..., description="Actual data payload")


__all__ = ["PolicyConfig", "StreamDataPoint"]