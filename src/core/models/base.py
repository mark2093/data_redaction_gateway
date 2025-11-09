"""
Base models and mixins.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field


class BaseModel(PydanticBaseModel):
    """Enhanced base model with common functionality."""
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        allow_population_by_field_name = True
        use_enum_values = True


class TimestampMixin(BaseModel):
    """Mixin for models that need timestamp tracking."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    def touch(self):
        """Update the timestamp."""
        self.updated_at = datetime.utcnow()


__all__ = ["BaseModel", "TimestampMixin"]