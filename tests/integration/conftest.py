"""Fixtures for integration tests."""
import pytest
from typing import AsyncGenerator, Dict, Any
import asyncio

from tests.utils import (
    get_test_housing_cooperative_data,
    get_auth_data,
    get_test_client,
    cleanup_database_record
)
from httpx import AsyncClient
from src.api.config import get_supabase

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_housing_cooperative() -> Dict[str, str]:
    """Fixture providing test data for housing cooperative."""
    return get_test_housing_cooperative_data()

@pytest.fixture(scope="session")
async def auth_credentials(event_loop) -> Dict[str, Any]:
    """Fixture providing authentication credentials for the entire test session."""
    credentials = await get_auth_data()
    yield credentials
    # Cleanup: Sign out at the end of the session
    supabase = await get_supabase()
    await supabase.auth.sign_out()

@pytest.fixture
async def test_client(auth_credentials) -> AsyncGenerator[AsyncClient, None]:
    """Fixture providing an async test client."""
    async with await get_test_client() as client:
        yield client

@pytest.fixture(autouse=True)
async def cleanup_housing_cooperative():
    """Fixture for cleaning up housing cooperative test data.
    
    This is an autouse fixture that will run before and after each test,
    ensuring cleanup even if the test fails.
    """
    # Clean up any existing data before the test
    test_data = get_test_housing_cooperative_data()
    await cleanup_database_record(
        table="housing_cooperatives",
        field="organisation_number",
        value=test_data["organisation_number"]
    )
    
    yield  # This allows the test to run
    
    # After yield is our teardown code
    await cleanup_database_record(
        table="housing_cooperatives",
        field="organisation_number",
        value=test_data["organisation_number"]
    ) 