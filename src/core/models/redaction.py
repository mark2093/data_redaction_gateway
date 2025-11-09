"""
Redaction-specific models.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import Field, validator
from enum import Enum

from .base import BaseModel


class RedactionAction(str, Enum):
    """Supported redaction actions."""
    MASK = "mask"
    TOKENIZE = "tokenize"
    ENCRYPT = "encrypt"
    HASH = "hash"
    FPE = "fpe"  # Format-Preserving Encryption


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


class JudgeResult(BaseModel):
    """Result from LLM-as-Judge validation."""
    coverage_complete: bool = Field(..., description="Whether all PII/PCI was redacted")
    over_redacted: bool = Field(..., description="Whether non-sensitive data was redacted")
    under_redacted: bool = Field(..., description="Whether sensitive data was missed")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence percentage")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    processing_time_ms: Optional[float] = Field(None, description="Judge processing time in ms")
    sampled: bool = Field(default=True, description="Whether this request was sampled")


__all__ = [
    "RedactionAction",
    "Severity", 
    "RedactionMeta",
    "RedactionRule",
    "JudgeResult",
]