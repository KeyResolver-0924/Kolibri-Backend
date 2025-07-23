import pytest
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import os
import asyncio
from dotenv import load_dotenv

from api.main import app
from api.config import get_supabase, initialize_supabase, get_settings, Settings

def pytest_configure(config):
    """Load test environment variables before any tests run"""
    if os.path.exists(".env"):
        print("\nLoading environment from .env")
        load_dotenv(".env", override=True)
    else:
        print("\nNo .env found, loading from .env")
        load_dotenv()
    
    # Verify Supabase configuration is loaded
    settings = get_settings()
    print(f"Loaded settings - Supabase URL: {settings.SUPABASE_URL}")
    print(f"Supabase key type: {'service_role' if 'service_role' in settings.SUPABASE_KEY else 'anon'}")
    print(f"Supabase key length: {len(settings.SUPABASE_KEY)}")

@pytest.fixture(scope="session")
def settings() -> Settings:
    """Return application settings"""
    return get_settings()

@pytest.fixture(scope="session")
def client(settings) -> TestClient:
    """Return a TestClient instance"""
    return TestClient(app)

@pytest.fixture(scope="function")
def setup_test_env():
    """Initialize Supabase with service role key for each test"""
    print("Starting up FastAPI application...")
    asyncio.run(initialize_supabase())
    yield
    # Cleanup if needed

@pytest.fixture
def integration_client(setup_test_env):
    """Real client for integration tests using actual Supabase"""
    app.dependency_overrides = {}  # Clear any existing overrides
    with TestClient(app) as client:
        yield client

@pytest.fixture
def mock_client(mock_supabase):
    """Client with mocked Supabase for unit tests"""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

# Mock Supabase response data
MOCK_DEED_ID = 1
MOCK_BORROWER_ID = 1

@pytest.fixture
def mock_deed_data():
    return {
        "id": MOCK_DEED_ID,
        "created_at": datetime.now().isoformat(),
        "credit_number": "CR123456",
        "housing_cooperative_id": 1,
        "apartment_address": "Test Street 123",
        "apartment_postal_code": "12345",
        "apartment_city": "Stockholm",
        "apartment_number": "1234",
        "status": "CREATED",
        "borrowers": [
            {
                "id": MOCK_BORROWER_ID,
                "deed_id": MOCK_DEED_ID,
                "name": "Test Person",
                "person_number": "198001011234",
                "email": "test@example.com",
                "ownership_percentage": Decimal("100"),
                "signing_status": "PENDING"
            }
        ]
    }

class MockResponse:
    def __init__(self, data=None, error=None):
        print(f"Creating MockResponse with data: {data}, error: {error}")
        self.data = data
        self.error = error

class AsyncMockQueryBuilder:
    def __init__(self, return_data=None):
        print(f"Creating AsyncMockQueryBuilder with return_data: {return_data}")
        self.return_data = return_data
        self._is_single = False
        self._filters = []
        self._error = None
        self._select_fields = None

    def select(self, *args):
        print(f"Select called with args: {args}")
        self._select_fields = args
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def delete(self):
        return self

    def single(self):
        print("Single called")
        self._is_single = True
        return self

    def eq(self, field, value):
        print(f"Eq called with field: {field}, value: {value}")
        self._filters.append(("eq", field, value))
        # Filter the data based on the eq condition
        if self.return_data and isinstance(self.return_data, dict):
            print(f"Checking field {field} in data: {self.return_data.get(field)} == {value}")
            if self.return_data.get(field) != value:
                print(f"Setting return_data to None because {field} doesn't match")
                self.return_data = None
        return self

    def in_(self, field, values):
        self._filters.append(("in", field, values))
        return self

    def range(self, start, end):
        self._filters.append(("range", start, end))
        return self

    def gte(self, field, value):
        self._filters.append(("gte", field, value))
        return self

    def lte(self, field, value):
        self._filters.append(("lte", field, value))
        return self

    def set_error(self, error):
        print(f"Setting error: {error}")
        self._error = error
        return self

    async def execute(self):
        print(f"Execute called. Error: {self._error}, Return data: {self.return_data}, Is single: {self._is_single}")
        if self._error:
            print(f"Raising error: {self._error}")
            raise self._error

        if self.return_data is None:
            print("Return data is None")
            if self._is_single:
                return MockResponse(None)
            return MockResponse([])
        
        if self._is_single:
            print("Single mode")
            if isinstance(self.return_data, list):
                data = self.return_data[0] if self.return_data else None
            else:
                data = self.return_data
            return MockResponse(data)
        
        if not isinstance(self.return_data, list):
            data = [self.return_data] if self.return_data is not None else []
        else:
            data = self.return_data
        
        return MockResponse(data)

class MockSupabase:
    def __init__(self):
        self._tables = {}
        self.current_builder = None

    def from_(self, name):
        print(f"From called with name: {name}")
        if name not in self._tables:
            print(f"Creating new query builder for {name}")
            self._tables[name] = AsyncMockQueryBuilder()
        builder = self._tables[name]
        print(f"Returning query builder with data: {builder.return_data}")
        return builder

    def table(self, name):
        return self.from_(name)

    def set_table_response(self, table_name, response_data):
        print(f"Setting table response for {table_name}: {response_data}")
        if table_name not in self._tables:
            self._tables[table_name] = AsyncMockQueryBuilder(response_data)
        else:
            self._tables[table_name].return_data = response_data

    def set_table_error(self, table_name, error):
        print(f"Setting table error for {table_name}: {error}")
        if table_name not in self._tables:
            self._tables[table_name] = AsyncMockQueryBuilder()
        self._tables[table_name].set_error(error)

@pytest.fixture
def mock_supabase():
    return MockSupabase()

@pytest.fixture
def mock_housing_cooperative_data():
    return {
        "id": 1,
        "organisation_number": "769600-1234",
        "name": "BRF Södermalm 14",
        "address": "Götgatan 100",
        "postal_code": "116 62",
        "city": "Stockholm",
        "administrator_name": "Eva Andersson",
        "administrator_person_number": "198001011234",
        "administrator_email": "eva.andersson@fastighetsservice.se"
    } 