#!/usr/bin/env python3
"""
Simple test to debug signing page issues
"""

import asyncio
import httpx
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.config import get_settings, get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def test_simple_signing():
    """Simple test to debug signing issues."""
    
    print("Testing Simple Signing Debug")
    print("=" * 30)
    
    # Test 1: Check if we can access the signing page
    print("\n1. Testing signing page with invalid token...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8080/api/signing/sign/invalid-token")
            print(f"Status: {response.status_code}")
            print(f"Content: {response.text[:200]}...")
            
            if response.status_code == 200:
                if "Invalid Token" in response.text:
                    print("✅ Correctly shows invalid token message")
                elif "Error" in response.text:
                    print("❌ Shows generic error - need to check logs")
                else:
                    print("✅ Page loads but content unclear")
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test 2: Check if we can create a real token and test it
    print("\n2. Creating and testing real token...")
    try:
        supabase = await get_supabase()
        
        # Get a deed and borrower
        deed_result = await handle_supabase_operation(
            operation_name="fetch test deed",
            operation=supabase.table("mortgage_deeds").select("id").limit(1).execute(),
            error_msg="Failed to fetch test deed"
        )
        
        if not deed_result.data:
            print("❌ No mortgage deeds found")
            return
        
        deed_id = deed_result.data[0]["id"]
        print(f"✅ Found deed ID: {deed_id}")
        
        # Get a borrower
        borrower_result = await handle_supabase_operation(
            operation_name="fetch test borrower",
            operation=supabase.table("borrowers").select("id, email").eq("deed_id", deed_id).limit(1).execute(),
            error_msg="Failed to fetch test borrower"
        )
        
        if not borrower_result.data:
            print("❌ No borrowers found")
            return
        
        borrower = borrower_result.data[0]
        print(f"✅ Found borrower: {borrower['email']}")
        
        # Create a test token
        import secrets
        from datetime import datetime, timedelta
        
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)
        
        signing_token_data = {
            "deed_id": deed_id,
            "borrower_id": borrower["id"],
            "token": token,
            "email": borrower["email"],
            "expires_at": expires_at.isoformat()
        }
        
        token_result = await handle_supabase_operation(
            operation_name="create test signing token",
            operation=supabase.table("signing_tokens").insert(signing_token_data).execute(),
            error_msg="Failed to create test signing token"
        )
        
        if token_result.data:
            print(f"✅ Created token: {token[:10]}...")
            
            # Test the signing page with real token
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8080/api/signing/sign/{token}")
                print(f"Signing page status: {response.status_code}")
                
                if response.status_code == 200:
                    if "Signera Pantbrev Digitalt" in response.text:
                        print("✅ Signing page works with real token")
                    else:
                        print("❌ Signing page missing button")
                        print(f"Content preview: {response.text[:500]}...")
                else:
                    print(f"❌ Signing page failed: {response.status_code}")
                    print(f"Response: {response.text}")
            
            # Clean up
            await handle_supabase_operation(
                operation_name="delete test token",
                operation=supabase.table("signing_tokens").delete().eq("token", token).execute(),
                error_msg="Failed to delete test token"
            )
            print("✅ Cleaned up test token")
            
        else:
            print("❌ Failed to create token")
            
    except Exception as e:
        print(f"❌ Error in token test: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_signing())
    print("\nTest completed!") 