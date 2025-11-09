"""
API-related models for requests and responses.
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import Field, validator

from .base import BaseModel
from .redaction import RedactionMeta, JudgeResult


class RedactionRequest(BaseModel):
    """Request model for redaction API."""
    data: Union[Dict[str, Any], List[Dict[str, Any]], str] = Field(
        ..., description="Data to be redacted (JSON object, array, or text)"
    )
    policy_version: Optional[str] = Field(None, description="Specific policy version to use")
    dry_run: bool = Field(default=False, description="If true, only show what would be redacted")
    include_meta: bool = Field(default=True, description="Include redaction metadata in response")
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "customer": {
                        "email": "john.doe@example.com",
                        "credit_card": "4111111111111111"
                    }
                },
                "include_meta": True
            }
        }


class RedactionResponse(BaseModel):
    """Response model for redacted data."""
    redacted_data: Union[Dict[str, Any], List[Dict[str, Any]], str] = Field(
        ..., description="Redacted data"
    )
    redaction_meta: Optional[List[RedactionMeta]] = Field(
        None, description="Metadata about redactions performed"
    )
    policy_version: str = Field(..., description="Policy version used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    judge_result: Optional[JudgeResult] = Field(None, description="LLM judge validation result")


class DryRunResponse(BaseModel):
    """Response model for dry-run mode."""
    original_data: Union[Dict[str, Any], List[Dict[str, Any]], str]
    redacted_data: Union[Dict[str, Any], List[Dict[str, Any]], str]
    diff: Dict[str, Any] = Field(..., description="Differences between original and redacted")
    redaction_meta: List[RedactionMeta]
    policy_version: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    policy_version: Optional[str] = Field(None, description="Current policy version")
    uptime_seconds: float = Field(..., description="Service uptime")
    cache_size: int = Field(default=0, description="Current cache size")


class MetricsResponse(BaseModel):
    """Enhanced metrics response with comprehensive observability data."""
    total_requests: int
    total_redactions: int
    avg_processing_time_ms: float = Field(alias="average_latency_ms")
    p95_latency_ms: float
    p99_latency_ms: float
    cache_hit_rate: float
    redaction_coverage: float
    judge_fallback_rate: float = Field(default=0.0, description="LLM fallback rate")
    judge_calls_total: int = Field(default=0, description="Total LLM judge calls")
    judge_fallbacks: int = Field(default=0, description="LLM judge fallbacks")
    
    class Config:
        populate_by_name = True  # Allow both field name and alias


__all__ = [
    "RedactionRequest",
    "RedactionResponse", 
    "DryRunResponse",
    "HealthResponse",
    "MetricsResponse",
]