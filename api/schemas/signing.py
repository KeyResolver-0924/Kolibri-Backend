from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class SigningTokenCreate(BaseModel):
    deed_id: int
    borrower_id: int
    email: EmailStr
    expires_at: datetime

class SigningTokenResponse(BaseModel):
    id: int
    deed_id: int
    borrower_id: int
    token: str
    email: str
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime

class BorrowerSignRequest(BaseModel):
    token: str
    signature_confirmed: bool = True

class BorrowerSignResponse(BaseModel):
    success: bool
    message: str
    deed_id: Optional[int] = None 
    borrower_name: Optional[str] = None
    signing_status: Optional[str] = None
    all_signed: Optional[bool] = None 