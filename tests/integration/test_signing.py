import pytest
from httpx import AsyncClient
import logging
from tests.utils import (
    get_test_housing_cooperative_data,
    get_test_mortgage_deed_data,
    get_auth_data,
    get_test_client,
    cleanup_database_record
)

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@pytest.mark.asyncio
async def test_signing_flow_initiation():
    """Test the initiation of the signing flow for a mortgage deed."""
    logger.info("Starting signing flow initiation test")
    
    # Get test client and auth data
    client = await get_test_client()
    auth_data = await get_auth_data()
    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
    
    try:
        # 1. Create a housing cooperative
        logger.info("Creating test housing cooperative")
        coop_data = get_test_housing_cooperative_data()
        # Update admin email to specified test email
        coop_data["administrator_email"] = "gbgmian+admin@gmail.com"
        
        response = await client.post(
            "/api/housing-cooperatives/",
            json=coop_data,
            headers=headers
        )
        assert response.status_code == 201, f"Failed to create housing cooperative: {response.text}"
        coop_id = response.json()["id"]
        logger.info(f"Created housing cooperative with ID: {coop_id}")
        
        # 2. Create a deed with one borrower
        logger.info("Creating test mortgage deed")
        deed_data = get_test_mortgage_deed_data(
            housing_cooperative_id=coop_id,
            borrowers=[{
                "name": "Anders Svensson",
                "person_number": "198001015678",
                "email": "gbgmian+borrower@gmail.com",
                "ownership_percentage": 50
            }, {
                "name": "Maria Andersson",
                "person_number": "198203034567",
                "email": "gbgmian+borrower@gmail.com",
                "ownership_percentage": 50
            }]
        )
        
        response = await client.post(
            "/api/mortgage-deeds/",
            json=deed_data,
            headers=headers
        )
        assert response.status_code == 201, f"Failed to create mortgage deed: {response.text}"
        deed_id = response.json()["id"]
        logger.info(f"Created mortgage deed with ID: {deed_id}")
        
        # 3. Initiate signing flow
        logger.info("Initiating signing flow")
        response = await client.post(
            f"/api/mortgage-deeds/deeds/{deed_id}/send-for-signing",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to initiate signing flow: {response.text}"
        deed_response = response.json()
        logger.info(f"Signing flow response: {deed_response}")
        
        # Verify deed status is updated
        assert deed_response["status"] == "PENDING_BORROWER_SIGNATURE"
        
        # 4. Sign as first borrower
        logger.info("Signing deed as first borrower (Anders Svensson)")
        sign_payload = {
            "person_number": "198001015678"  # Matches the borrower in deed_data
        }
        response = await client.post(
            f"/api/mortgage-deeds/{deed_id}/signatures/borrower",
            json=sign_payload,
            headers=headers
        )
        assert response.status_code == 200, f"Failed to sign as first borrower: {response.text}"
        borrower_sign_response = response.json()
        logger.info(f"First borrower signing response: {borrower_sign_response}")
        # Status should still be PENDING_BORROWER_SIGNATURE as second borrower hasn't signed
        assert borrower_sign_response["status"] == "PENDING_BORROWER_SIGNATURE"
        
        # 5. Sign as second borrower
        logger.info("Signing deed as second borrower (Maria Andersson)")
        sign_payload = {
            "person_number": "198203034567"  # Matches the second borrower
        }
        response = await client.post(
            f"/api/mortgage-deeds/{deed_id}/signatures/borrower",
            json=sign_payload,
            headers=headers
        )
        assert response.status_code == 200, f"Failed to sign as second borrower: {response.text}"
        borrower_sign_response = response.json()
        logger.info(f"Second borrower signing response: {borrower_sign_response}")
        # Now status should change to PENDING_HOUSING_COOPERATIVE_SIGNATURE
        assert borrower_sign_response["status"] == "PENDING_HOUSING_COOPERATIVE_SIGNATURE"
        
        # 6. Sign as cooperative administrator
        logger.info("Signing deed as cooperative administrator")
        coop_sign_payload = {
            "person_number": coop_data["administrator_person_number"]
        }
        response = await client.post(
            f"/api/mortgage-deeds/{deed_id}/signatures/cooperative-admin",
            json=coop_sign_payload,
            headers=headers
        )
        assert response.status_code == 200, f"Failed to sign as cooperative admin: {response.text}"
        admin_sign_response = response.json()
        logger.info(f"Cooperative admin signing response: {admin_sign_response}")
        assert admin_sign_response["status"] == "COMPLETED"

        # 7. Fetch deed to confirm final status
        logger.info("Fetching deed to confirm completion")
        response = await client.get(f"/api/mortgage-deeds/{deed_id}", headers=headers)
        assert response.status_code == 200, f"Failed to fetch deed: {response.text}"
        final_deed_data = response.json()
        logger.info(f"Final deed data: {final_deed_data}")
        assert final_deed_data["status"] == "COMPLETED", "Deed did not reach COMPLETED status"

    finally:
        # Cleanup test data
        logger.info("Cleaning up test data")
        if 'deed_id' in locals():
            await cleanup_database_record("mortgage_deeds", "id", deed_id)
        if 'coop_id' in locals():
            await cleanup_database_record("housing_cooperatives", "id", coop_id) 