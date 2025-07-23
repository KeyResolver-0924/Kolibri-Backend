"""Integration tests for housing cooperative endpoints."""
import pytest
from httpx import AsyncClient
from typing import Dict, Any

pytestmark = pytest.mark.asyncio

class TestHousingCooperative:
    """Test cases for housing cooperative endpoints."""
    
    async def test_create_and_retrieve_housing_cooperative(
        self,
        test_client: AsyncClient,
        test_housing_cooperative: Dict[str, str],
        auth_credentials: Dict[str, Any],
        cleanup_housing_cooperative: None,
    ) -> None:
        """Test creating and retrieving a housing cooperative.
        
        Args:
            test_client: Async HTTP client fixture
            test_housing_cooperative: Test data fixture
            auth_credentials: Authentication credentials fixture
            cleanup_housing_cooperative: Cleanup fixture
        """
        # Create housing cooperative
        response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        
        # Verify creation response
        assert response.status_code == 201
        data = response.json()
        
        # Verify response data matches input
        for key, value in test_housing_cooperative.items():
            assert data[key] == value
        
        # Verify ID field
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["id"] > 0

        # Verify retrieval
        get_response = await test_client.get(
            f"/api/housing-cooperatives/{data['organisation_number']}/",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert get_response.status_code == 200
        assert get_response.json() == data

    async def test_list_housing_cooperatives(
        self,
        test_client: AsyncClient,
        test_housing_cooperative: Dict[str, str],
        auth_credentials: Dict[str, Any],
        cleanup_housing_cooperative: None,
    ) -> None:
        """Test listing housing cooperatives with pagination."""
        # Create a housing cooperative first
        create_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert create_response.status_code == 201

        # Test listing with pagination
        list_response = await test_client.get(
            "/api/housing-cooperatives/?page=1&page_size=10",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert list_response.status_code == 200
        data = list_response.json()
        
        # Verify pagination headers
        assert "X-Total-Count" in list_response.headers
        assert "X-Total-Pages" in list_response.headers
        assert "X-Current-Page" in list_response.headers
        assert "X-Page-Size" in list_response.headers
        
        # Verify the created cooperative is in the list
        assert any(coop["organisation_number"] == test_housing_cooperative["organisation_number"] 
                  for coop in data)

    async def test_update_housing_cooperative(
        self,
        test_client: AsyncClient,
        test_housing_cooperative: Dict[str, str],
        auth_credentials: Dict[str, Any],
        cleanup_housing_cooperative: None,
    ) -> None:
        """Test updating a housing cooperative."""
        # Create a housing cooperative first
        create_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert create_response.status_code == 201
        
        # Update the cooperative
        updated_data = {
            "name": "Updated Name",
            "address": "Updated Address 123",
            "city": "Updated City"
        }
        update_response = await test_client.put(
            f"/api/housing-cooperatives/{test_housing_cooperative['organisation_number']}/",
            json=updated_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        
        # Verify updated fields
        assert updated["name"] == updated_data["name"]
        assert updated["address"] == updated_data["address"]
        assert updated["city"] == updated_data["city"]
        # Verify unchanged fields
        assert updated["organisation_number"] == test_housing_cooperative["organisation_number"]

    async def test_delete_housing_cooperative(
        self,
        test_client: AsyncClient,
        test_housing_cooperative: Dict[str, str],
        auth_credentials: Dict[str, Any],
    ) -> None:
        """Test deleting a housing cooperative."""
        # Create a housing cooperative first
        create_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert create_response.status_code == 201
        
        # Delete the cooperative
        delete_response = await test_client.delete(
            f"/api/housing-cooperatives/{test_housing_cooperative['organisation_number']}/",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert delete_response.status_code == 204
        
        # Verify cooperative is deleted
        get_response = await test_client.get(
            f"/api/housing-cooperatives/{test_housing_cooperative['organisation_number']}/",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert get_response.status_code == 404

    async def test_error_cases(
        self,
        test_client: AsyncClient,
        test_housing_cooperative: Dict[str, str],
        auth_credentials: Dict[str, Any],
        cleanup_housing_cooperative: None,
    ) -> None:
        """Test various error cases."""
        # Test creating duplicate cooperative
        # First create one
        create_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert create_response.status_code == 201
        
        # Try to create duplicate
        duplicate_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert duplicate_response.status_code == 409
        
        # Test invalid organization number format
        invalid_data = test_housing_cooperative.copy()
        invalid_data["organisation_number"] = "123"  # Too short
        invalid_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=invalid_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert invalid_response.status_code == 422
        
        # Test updating non-existent cooperative
        non_existent_response = await test_client.put(
            "/api/housing-cooperatives/999999-9999/",
            json={"name": "New Name"},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert non_existent_response.status_code == 404 