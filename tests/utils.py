"""Common test utilities for integration and unit tests."""
from typing import Dict, Any, List
from httpx import AsyncClient, ASGITransport
import time

from src.api.main import app
from src.api.config import get_settings, get_supabase

settings = get_settings()

def get_test_housing_cooperative_data(organisation_number: str = None) -> Dict[str, str]:
    """Get test data for creating a housing cooperative."""
    if organisation_number is None:
        # Generate a unique organization number using timestamp
        timestamp = int(time.time())
        # Format: XXXXXX-XXXX
        organisation_number = f"{str(timestamp)[-10:-4]}-{str(timestamp)[-4:]}"
    
    return {
        "name": "Test Housing Cooperative",
        "organisation_number": organisation_number,
        "address": "Testgatan 123",
        "postal_code": "123 45",
        "city": "Teststad",
        "administrator_name": "Eva Lindberg",
        "administrator_person_number": "196505055555",
        "administrator_email": "gbgmian+admin@gmail.com",
        "administrator_company": "Admin AB"
    }

def get_test_borrower_data(person_number: str = "19800101-1234") -> Dict[str, str]:
    """Get test data for a borrower.
    
    Args:
        person_number: The person number to use for the borrower
        
    Returns:
        Dict containing test borrower data
    """
    return {
        "person_number": person_number,
        "first_name": "Anna",
        "last_name": "Andersson",
        "email": f"anna.{person_number}@example.com",
        "phone_number": "+46701234567",
        "address": "Storgatan 1",
        "postal_code": "411 15",
        "city": "Göteborg"
    }

def get_test_mortgage_deed_data(housing_cooperative_id: int, borrowers: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get test data for creating a mortgage deed.
    
    Args:
        housing_cooperative_id: ID of the housing cooperative
        borrowers: Optional list of borrower data. If not provided, default test borrowers will be used.
    
    Returns:
        Dict containing test mortgage deed data
    """
    # Generate a unique credit number using timestamp and a counter
    timestamp = int(time.time())
    # Use a class variable to ensure unique numbers across multiple calls
    if not hasattr(get_test_mortgage_deed_data, 'counter'):
        get_test_mortgage_deed_data.counter = 0
    get_test_mortgage_deed_data.counter += 1
    
    # Combine timestamp with counter to ensure uniqueness
    credit_number = f"2024-{str(timestamp)[-6:]}-{get_test_mortgage_deed_data.counter}"
    
    # Use default borrowers if none provided
    default_borrowers = [
        {
            "name": "Anna Andersson",
            "person_number": "198001015678",
            "email": "anna.andersson@example.com",
            "ownership_percentage": 50
        },
        {
            "name": "Erik Eriksson",
            "person_number": "197002025678",
            "email": "erik.eriksson@example.com",
            "ownership_percentage": 50
        }
    ]
    
    return {
        "credit_number": credit_number,
        "housing_cooperative_id": housing_cooperative_id,
        "apartment_address": "Storgatan 1",
        "apartment_postal_code": "411 15",
        "apartment_city": "Göteborg",
        "apartment_number": "1001",
        "borrowers": borrowers if borrowers is not None else default_borrowers
    }

async def get_auth_data() -> Dict[str, Any]:
    """Get authenticated user and token from Supabase.
    
    Returns:
        Dict containing user data and access token
    """
    try:
        supabase = await get_supabase()
        auth_response = await supabase.auth.sign_in_with_password({
            "email": "gbgmian@gmail.com",
            "password": "kolibri123"
        })
        
        user = auth_response.user
        session = auth_response.session
       
        return {
            "access_token": session.access_token,
            "user": user,
            "bank_id": user.user_metadata.get("bank_id")
        }
    except Exception as e:
        print(f"Auth error: {str(e)}")
        raise

async def get_other_bank_auth_data() -> Dict[str, Any]:
    """Get authenticated user and token for a different bank from Supabase.
    
    Returns:
        Dict containing user data and access token for a different bank
    """
    try:
        supabase = await get_supabase()
        auth_response = await supabase.auth.sign_in_with_password({
            "email": "gbgmian+2@gmail.com",
            "password": "kolibri123"
        })
        
        user = auth_response.user
        session = auth_response.session
       
        return {
            "access_token": session.access_token,
            "user": user,
            "bank_id": user.user_metadata.get("bank_id")
        }
    except Exception as e:
        print(f"Auth error: {str(e)}")
        raise

async def get_test_client() -> AsyncClient:
    """Get an async test client for the FastAPI app.
    
    Returns:
        AsyncClient instance
    """
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True
    )

async def cleanup_database_record(table: str, field: str, value: str) -> None:
    """Clean up a test record from the database.
    
    Args:
        table: The table to delete from
        field: The field to match on
        value: The value to match
    """
    try:
        supabase = await get_supabase()
        await supabase.table(table).delete().eq(field, value).execute()
    except Exception as e:
        print(f"Cleanup error: {str(e)}")
        # Don't raise the error as this is cleanup code 