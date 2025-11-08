"""
Pydantic models for the PII/PCI Data Redaction Gateway.
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class RedactionAction(str, Enum):
    """Supported redaction actions."""
    MASK = "mask"
    TOKENIZE = "tokenize"
    ENCRYPT = "encrypt"
    HASH = "hash"


class Severity(str, Enum):
    """Rule severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RedactionMeta(BaseModel):
    """Metadata about a redaction operation."""
    field: str = Field(..., description="JSONPath or field name that was redacted")
    rule: str = Field(..., description="Rule ID that triggered the redaction")
    action: RedactionAction = Field(..., description="Action taken")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RedactionRule(BaseModel):
    """Definition of a single redaction rule."""
    id: str = Field(..., description="Unique rule identifier")
    pattern: Optional[str] = Field(None, description="Regex pattern for detection")
    engine: Optional[str] = Field(None, description="Detection engine (e.g., 'NER', 'LUHN')")
    model: Optional[str] = Field(None, description="Model name for NER engine")
    action: RedactionAction = Field(default=RedactionAction.MASK)
    severity: Severity = Field(default=Severity.MEDIUM)
    tags: List[str] = Field(default_factory=list, description="Compliance tags")
    enabled: bool = Field(default=True)
    mask_config: Optional[Dict[str, Any]] = Field(None, description="Masking configuration")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional rule metadata")
    
    @validator('pattern', 'engine')
    def check_pattern_or_engine(cls, v, values):
        """Ensure either pattern or engine is provided."""
        return v
    
    def model_post_init(self, __context):
        """Post-initialization to move mask_config to metadata."""
        if self.mask_config:
            if self.metadata is None:
                self.metadata = {}
            self.metadata['mask_config'] = self.mask_config


class PolicyConfig(BaseModel):
    """Policy configuration from YAML."""
    version: str = Field(..., description="Policy version")
    effective_date: Optional[str] = Field(None)
    rules: List[RedactionRule] = Field(..., description="List of redaction rules")
    
    class Config:
        extra = "allow"


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


class JudgeResult(BaseModel):
    """Result from LLM-as-Judge validation."""
    coverage_complete: bool = Field(..., description="Whether all PII/PCI was redacted")
    over_redacted: bool = Field(..., description="Whether non-sensitive data was redacted")
    under_redacted: bool = Field(..., description="Whether sensitive data was missed")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence percentage")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    processing_time_ms: Optional[float] = Field(None, description="Judge processing time in ms")
    sampled: bool = Field(default=True, description="Whether this request was sampled")


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
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


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
    """Metrics response."""
    total_requests: int
    total_redactions: int
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    cache_hit_rate: float
    redaction_coverage: float
    judge_fallback_rate: float = Field(default=0.0, description="LLM fallback rate")


class StreamDataPoint(BaseModel):
    """Model for simulated stream data point."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_type: str = Field(..., description="Type of data (order, transaction, chat)")
    payload: Dict[str, Any] = Field(..., description="Actual data payload")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
