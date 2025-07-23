from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re

class HousingCooperativeBase(BaseModel):
    organisation_number: str = Field(
        ..., 
        description="Organization number of the housing cooperative",
        min_length=10,
        max_length=11
    )
    name: str = Field(
        ..., 
        description="Name of the housing cooperative",
        min_length=2,
        max_length=100
    )
    address: str = Field(
        ..., 
        description="Address of the housing cooperative",
        min_length=5,
        max_length=200
    )
    city: str = Field(
        ..., 
        description="City of the housing cooperative",
        min_length=2,
        max_length=100
    )
    postal_code: str = Field(
        ..., 
        description="Postal code of the housing cooperative"
    )
    administrator_company: Optional[str] = Field(
        None, 
        description="Administrator company name",
        max_length=100
    )
    administrator_name: str = Field(
        ..., 
        description="Name of the administrator",
        min_length=2,
        max_length=100
    )
    administrator_person_number: str = Field(
        ..., 
        description="Personal number of the administrator"
    )
    administrator_email: EmailStr = Field(
        ..., 
        description="Email of the administrator"
    )

    @field_validator('postal_code')
    def validate_postal_code(cls, v: str) -> str:
        # Remove any whitespace and check if it's 5 digits
        cleaned = v.replace(" ", "")
        if not re.match(r'^\d{5}$', cleaned):
            raise ValueError('Postal code must be 5 digits, optionally separated by space (e.g., "123 45" or "12345")')
        return v  # Return original format to preserve user input

    @field_validator('organisation_number')
    def validate_organisation_number(cls, v: str) -> str:
        if not re.match(r'^\d{6}-\d{4}$', v):
            raise ValueError('Organization number must be in format XXXXXX-XXXX')
        return v

    @field_validator('administrator_person_number')
    def validate_person_number(cls, v: str) -> str:
        # Check both formats: YYYYMMDDXXXX and YYYYMMDD-XXXX
        if not re.match(r'^\d{8}[-]?\d{4}$', v):
            raise ValueError('Person number must be in format YYYYMMDDXXXX or YYYYMMDD-XXXX')
        return v

    @field_validator('administrator_company')
    def validate_administrator_company(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        if len(v.strip()) < 2:
            raise ValueError('Administrator company name must be at least 2 characters if provided')
        return v.strip()

class HousingCooperativeCreate(HousingCooperativeBase):
    pass

class HousingCooperativeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Name of the housing cooperative")
    address: Optional[str] = Field(None, min_length=5, max_length=200, description="Address of the housing cooperative")
    city: Optional[str] = Field(None, min_length=2, max_length=100, description="City of the housing cooperative")
    postal_code: Optional[str] = Field(None, description="Postal code of the housing cooperative")
    administrator_company: Optional[str] = Field(
        None, 
        description="Administrator company name",
        max_length=100
    )
    administrator_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Name of the administrator")
    administrator_person_number: Optional[str] = Field(None, description="Personal number of the administrator")
    administrator_email: Optional[EmailStr] = Field(None, description="Email of the administrator")

    @field_validator('administrator_company')
    def validate_administrator_company(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        if len(v.strip()) < 2:
            raise ValueError('Administrator company name must be at least 2 characters if provided')
        return v.strip()

class HousingCooperativeResponse(HousingCooperativeBase):
    id: int = Field(..., gt=0) 