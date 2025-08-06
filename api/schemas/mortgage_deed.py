from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import List, Optional, Literal
from datetime import datetime
from decimal import Decimal
import re
from uuid import UUID

# Status enums
DeedStatus = Literal[
    "CREATED",
    "PENDING_BORROWER_SIGNATURE",
    "PENDING_HOUSING_COOPERATIVE_SIGNATURE",
    "COMPLETED"
]

SigningStatus = Literal[
    "PENDING",
    "SIGNED",
    "REJECTED"
]

class AuditLogCreate(BaseModel):
    deed_id: int
    action_type: str
    user_id: UUID

class AuditLogResponse(AuditLogCreate):
    id: int
    timestamp: datetime
    description: str

class BorrowerCreate(BaseModel):
    name: str
    person_number: str = Field(pattern=r'^\d{12}$')  # Swedish personal number format
    email: EmailStr
    ownership_percentage: Decimal = Field(gt=0, le=100)

    @field_validator('person_number')
    @classmethod
    def validate_person_number(cls, v):
        if not re.match(r'^\d{12}$', v):
            raise ValueError('Person number must be exactly 12 digits')
        return v

class BorrowerResponse(BorrowerCreate):
    id: int
    deed_id: int
    signature_timestamp: Optional[datetime] = None

class HousingCooperativeSignerCreate(BaseModel):
    administrator_name: str
    administrator_person_number: str
    administrator_email: str

class HousingCooperativeSignerResponse(HousingCooperativeSignerCreate):
    id: int
    mortgage_deed_id: int
    signature_timestamp: Optional[datetime] 

class AccountingFirmSignerCreate(BaseModel):
    accounting_firm_name: str
    accounting_firm_email: str

class AccountingFirmSignerResponse(AccountingFirmSignerCreate):
    id: int
    mortgage_deed_id: int
    signature_timestamp: Optional[datetime] = None

class MortgageDeedCreate(BaseModel):
    credit_number: str
    credit_numbers: List[str]
    add_more_credit_numbers: bool
    housing_cooperative_id: int
    is_accounting_firm: bool
    borrowers: List[BorrowerCreate]
    housing_cooperative_signers: List[HousingCooperativeSignerCreate]
    has_existing_mortgages: bool
    existing_mortgage_bank: str
    existing_mortgage_date: str
    notes: str
    organization_number: str
    cooperative_name: str
    cooperative_address: str
    cooperative_postal_code: str
    cooperative_city: str
    apartment_address: str
    apartment_number: str
    apartment_postal_code: str
    apartment_city: str
    accounting_firm_name: Optional[str] = None
    accounting_firm_email: Optional[str] = None


class HousingCooperativeResponse(BaseModel):
    id: int
    name: str
    organisation_number: str
    address: str
    postal_code: str
    city: str
    administrator_name: Optional[str]
    administrator_person_number: Optional[str]
    administrator_email: Optional[str]
    administrator_company: Optional[str]

class MortgageDeedResponse(BaseModel):
    id: int
    created_at: datetime
    credit_number: str
    housing_cooperative_id: int
    housing_cooperative: Optional[HousingCooperativeResponse]
    apartment_address: str
    apartment_postal_code: str
    apartment_city: str
    apartment_number: str
    status: DeedStatus
    bank_id: int
    borrowers: List[BorrowerResponse]
    housing_cooperative_signers: List[HousingCooperativeSignerResponse]
    accounting_firm_signers: List[AccountingFirmSignerResponse]

class MortgageDeedUpdate(BaseModel):
    apartment_address: Optional[str] = None
    apartment_postal_code: Optional[str] = None
    apartment_city: Optional[str] = None
    apartment_number: Optional[str] = None
    housing_cooperative_id: Optional[int] = None
    borrowers: Optional[List[BorrowerCreate]] = None
    housing_cooperative_signers: Optional[List[HousingCooperativeSignerCreate]] = None

    @model_validator(mode='after')
    def validate_ownership_percentages(self):
        if hasattr(self, 'borrowers') and self.borrowers:
            total_percentage = sum(float(borrower.ownership_percentage) for borrower in self.borrowers)
            if abs(total_percentage - 100) > 0.01:  # Allow for small floating point differences
                raise ValueError('Total ownership percentage must equal 100')
        return self 

class SignRequest(BaseModel):
    person_number: str = Field(pattern=r'^\d{12}$')  # Swedish personal number format

    @field_validator('person_number')
    @classmethod
    def validate_person_number(cls, v):
        if not re.match(r'^\d{12}$', v):
            raise ValueError('Person number must be exactly 12 digits')
        return v

class SignResponse(BaseModel):
    deed_id: int
    status: DeedStatus
    message: str 