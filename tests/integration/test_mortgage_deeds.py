"""Integration tests for mortgage deed endpoints."""
import pytest
from httpx import AsyncClient
from typing import Dict, Any

from tests.utils import (
    get_test_housing_cooperative_data,
    get_test_mortgage_deed_data,
    get_test_borrower_data,
    get_other_bank_auth_data
)

pytestmark = pytest.mark.asyncio

class TestMortgageDeed:
    """Test cases for mortgage deed endpoints."""
    
    async def test_create_and_retrieve_mortgage_deed(
        self,
        test_client: AsyncClient,
        auth_credentials: Dict[str, Any],
    ) -> None:
        """Test creating and retrieving a mortgage deed with two borrowers."""
        # First create a housing cooperative
        test_housing_cooperative = get_test_housing_cooperative_data()
        coop_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert coop_response.status_code == 201
        coop_data = coop_response.json()
        
        # Create mortgage deed data with two borrowers
        mortgage_deed_data = get_test_mortgage_deed_data(
            housing_cooperative_id=coop_data["id"]
        )
        
        # Create mortgage deed
        response = await test_client.post(
            "/api/mortgage-deeds/",
            json=mortgage_deed_data,
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
        assert data["housing_cooperative_id"] == mortgage_deed_data["housing_cooperative_id"]
        assert data["credit_number"] == mortgage_deed_data["credit_number"]
        assert data["apartment_address"] == mortgage_deed_data["apartment_address"]
        assert data["apartment_postal_code"] == mortgage_deed_data["apartment_postal_code"]
        assert data["apartment_city"] == mortgage_deed_data["apartment_city"]
        assert data["apartment_number"] == mortgage_deed_data["apartment_number"]
        assert len(data["borrowers"]) == 2
        assert data["status"] == "CREATED"  # Default status from schema
        
        # Verify ID field
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["id"] > 0
        
        # Verify retrieval
        get_response = await test_client.get(
            f"/api/mortgage-deeds/{data['id']}/",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert get_response.status_code == 200
        assert get_response.json() == data

    async def test_list_mortgage_deeds(
        self,
        test_client: AsyncClient,
        auth_credentials: Dict[str, Any],
    ) -> None:
        """Test listing mortgage deeds with pagination and bank_id filtering."""
        # First create a housing cooperative
        test_housing_cooperative = get_test_housing_cooperative_data()
        coop_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert coop_response.status_code == 201
        coop_data = coop_response.json()
        
        # Create two mortgage deeds for the current bank
        current_bank_deeds = []
        for _ in range(2):
            mortgage_deed_data = get_test_mortgage_deed_data(
                housing_cooperative_id=coop_data["id"]
            )
            create_response = await test_client.post(
                "/api/mortgage-deeds/",
                json=mortgage_deed_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {auth_credentials['access_token']}"
                }
            )
            assert create_response.status_code == 201
            current_bank_deeds.append(create_response.json())

        # Get auth credentials for other bank
        other_bank_auth = await get_other_bank_auth_data()

        # Create a mortgage deed for a different bank
        other_bank_deed_data = get_test_mortgage_deed_data(
            housing_cooperative_id=coop_data["id"]
        )
        other_bank_response = await test_client.post(
            "/api/mortgage-deeds/",
            json=other_bank_deed_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {other_bank_auth['access_token']}"
            }
        )
        assert other_bank_response.status_code == 201

        # Get the credit numbers for our test deeds
        test_credit_numbers = [deed["credit_number"] for deed in current_bank_deeds]
        test_credit_numbers.append(other_bank_response.json()["credit_number"])

        # Print debug information
        print(f"\nCurrent user bank_id: {auth_credentials['bank_id']}")
        print(f"Current bank deed bank_ids: {[deed.get('bank_id') for deed in current_bank_deeds]}")
        print(f"Other bank user bank_id: {other_bank_auth['bank_id']}")
        print(f"Other bank deed bank_id: {other_bank_response.json().get('bank_id')}")

        # Test listing with pagination, filtering by our test credit numbers
        list_response = await test_client.get(
            f"/api/mortgage-deeds/?page=1&page_size=10&credit_numbers={','.join(test_credit_numbers)}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert list_response.status_code == 200
        data = list_response.json()
        
        # Print response data for debugging
        print("\nResponse data bank_ids:", [deed.get('bank_id') for deed in data])
        
        # Verify pagination headers
        assert "X-Total-Count" in list_response.headers
        assert "X-Total-Pages" in list_response.headers
        assert "X-Current-Page" in list_response.headers
        assert "X-Page-Size" in list_response.headers
        
        # Verify only deeds from the current bank are returned
        assert len(data) == 2
        returned_deed_ids = {deed["id"] for deed in data}
        current_bank_deed_ids = {deed["id"] for deed in current_bank_deeds}
        assert returned_deed_ids == current_bank_deed_ids

        # Verify the deed from other bank is not in the list
        other_bank_deed = other_bank_response.json()
        assert other_bank_deed["id"] not in returned_deed_ids

        # Now test listing from the other bank's perspective
        other_bank_list_response = await test_client.get(
            f"/api/mortgage-deeds/?page=1&page_size=10&credit_numbers={','.join(test_credit_numbers)}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {other_bank_auth['access_token']}"
            }
        )
        assert other_bank_list_response.status_code == 200
        other_bank_data = other_bank_list_response.json()
        
        # Print response data for debugging
        print("\nOther bank response data bank_ids:", [deed.get('bank_id') for deed in other_bank_data])
        
        # Verify only the deed from the other bank is returned
        assert len(other_bank_data) == 1
        assert other_bank_data[0]["id"] == other_bank_deed["id"]
        
        # Verify the deeds from the first bank are not in the list
        other_bank_returned_ids = {deed["id"] for deed in other_bank_data}
        for deed in current_bank_deeds:
            assert deed["id"] not in other_bank_returned_ids

    async def test_update_mortgage_deed(
        self,
        test_client: AsyncClient,
        auth_credentials: Dict[str, Any],
    ) -> None:
        """Test updating a mortgage deed."""
        # First create a housing cooperative
        test_housing_cooperative = get_test_housing_cooperative_data()
        coop_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert coop_response.status_code == 201
        coop_data = coop_response.json()
        
        # Create a mortgage deed
        mortgage_deed_data = get_test_mortgage_deed_data(
            housing_cooperative_id=coop_data["id"]
        )
        create_response = await test_client.post(
            "/api/mortgage-deeds/",
            json=mortgage_deed_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert create_response.status_code == 201
        created_deed = create_response.json()
        
        # Update the deed
        updated_data = {
            "apartment_address": "Avenyn 1",
            "apartment_postal_code": "411 20",
            "apartment_city": "Göteborg",
            "apartment_number": "1002"
        }
        update_response = await test_client.put(
            f"/api/mortgage-deeds/{created_deed['id']}/",
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
        assert updated["apartment_address"] == updated_data["apartment_address"]
        assert updated["apartment_postal_code"] == updated_data["apartment_postal_code"]
        assert updated["apartment_city"] == updated_data["apartment_city"]
        assert updated["apartment_number"] == updated_data["apartment_number"]
        # Verify unchanged fields
        assert updated["id"] == created_deed["id"]
        assert updated["housing_cooperative_id"] == created_deed["housing_cooperative_id"]
        assert updated["credit_number"] == created_deed["credit_number"]
        assert updated["borrowers"] == created_deed["borrowers"]

    async def test_delete_mortgage_deed(
        self,
        test_client: AsyncClient,
        auth_credentials: Dict[str, Any],
    ) -> None:
        """Test deleting a mortgage deed."""
        # First create a housing cooperative
        test_housing_cooperative = get_test_housing_cooperative_data()
        coop_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert coop_response.status_code == 201
        coop_data = coop_response.json()
        
        # Create a mortgage deed
        mortgage_deed_data = get_test_mortgage_deed_data(
            housing_cooperative_id=coop_data["id"]
        )
        create_response = await test_client.post(
            "/api/mortgage-deeds/",
            json=mortgage_deed_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert create_response.status_code == 201
        created_deed = create_response.json()
        
        # Delete the deed
        delete_response = await test_client.delete(
            f"/api/mortgage-deeds/{created_deed['id']}/",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert delete_response.status_code == 204
        
        # Verify deed is deleted
        get_response = await test_client.get(
            f"/api/mortgage-deeds/{created_deed['id']}/",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert get_response.status_code == 404

    async def test_error_cases(
        self,
        test_client: AsyncClient,
        auth_credentials: Dict[str, Any],
    ) -> None:
        """Test various error cases for mortgage deeds."""
        # First create a housing cooperative
        test_housing_cooperative = get_test_housing_cooperative_data()
        coop_response = await test_client.post(
            "/api/housing-cooperatives/",
            json=test_housing_cooperative,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert coop_response.status_code == 201
        coop_data = coop_response.json()
        
        # Test creating deed with invalid housing cooperative ID
        invalid_deed_data = get_test_mortgage_deed_data(
            housing_cooperative_id=99999  # Non-existent ID
        )
        invalid_response = await test_client.post(
            "/api/mortgage-deeds/",
            json=invalid_deed_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert invalid_response.status_code == 404
        
        # Test creating deed with invalid borrower data
        invalid_borrower_data = get_test_mortgage_deed_data(
            housing_cooperative_id=coop_data["id"],
            borrowers=[
                {
                    "person_number": "invalid",  # Invalid format
                    "first_name": "Test",
                    "last_name": "Testsson"
                }
            ]
        )
        invalid_borrower_response = await test_client.post(
            "/api/mortgage-deeds/",
            json=invalid_borrower_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert invalid_borrower_response.status_code == 422
        
        # Test updating non-existent deed
        non_existent_response = await test_client.put(
            "/api/mortgage-deeds/99999/",
            json={"amount": 1000000},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {auth_credentials['access_token']}"
            }
        )
        assert non_existent_response.status_code == 404 