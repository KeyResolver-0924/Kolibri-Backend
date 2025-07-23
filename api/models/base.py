from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class TimestampedModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class AuditLogEntry(BaseModel):
    """Model for audit log entries."""
    deed_id: str
    action_type: str
    actor: str
    timestamp: datetime
    details: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True) 