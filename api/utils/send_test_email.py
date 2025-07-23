import sys
from pathlib import Path
import requests
# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
import asyncio
import os
from typing import Dict, Any
from api.config import Settings
from api.utils.email_utils import send_email

# Load environment variables
load_dotenv()

async def send_test_email() -> None:
    """Send a test email using the borrower sign template"""
    settings = Settings()
    
    # Test data for the template
    template_context: Dict[str, Any] = {
        "deed": {
            "reference_number": "TEST-123",
            "apartment_number": "1234",
            "apartment_address": "Testgatan 123, 123 45 Göteborg",
            "cooperative_name": "BRF Teståsen",
            "borrowers": [
                {
                    "name": "Test Testsson",
                    "signature_timestamp": None
                },
                {
                    "name": "Anna Andersson",
                    "signature_timestamp": "2024-01-20T14:30:00"
                }
            ]
        },
        "signing_url": "http://localhost:3000/deeds/1/sign"
    }
    
    success = await send_email(
        recipient_email="justinwang.tech@gmail.com",
        subject="Test Email - Pantbrev kräver din signatur",
        template_name="borrower_sign.html",
        template_context=template_context,
        settings=settings
    )
    
    if success:
        print("Test email sent successfully!")
    else:
        print("Failed to send test email")

if __name__ == "__main__":
    asyncio.run(send_test_email()) 