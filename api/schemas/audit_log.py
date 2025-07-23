from pydantic import BaseModel, UUID4
from datetime import datetime

class AuditLogBase(BaseModel):
    deed_id: int
    action_type: str
    user_id: UUID4

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: int
    timestamp: datetime 