#!/usr/bin/env python3
"""
Test script to verify the complete signing flow
"""

import asyncio
import httpx
import json
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.config import get_settings, get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def test_signing_flow():
    """Test the complete signing flow."""
    
    print("Testing Complete Signing Flow")
    print("=" * 40)
    
    # Test 1: Check if signing_tokens table exists
    print("\n1. Checking signing_tokens table...")
    try:
        supabase = await get_supabase()
        result = await handle_supabase_operation(
            operation_name="check signing_tokens table",
            operation=supabase.table("signing_tokens").select("id").limit(1).execute(),
            error_msg="Failed to access signing_tokens table"
        )
        print("✅ signing_tokens table exists and is accessible")
    except Exception as e:
        print(f"❌ signing_tokens table error: {e}")
        print("Please run the create_signing_tokens_table.sql script in your Supabase database")
        return
    
    # Test 2: Check if we can create a test signing token
    print("\n2. Testing signing token creation...")
    try:
        # First, get a deed and borrower
        deed_result = await handle_supabase_operation(
            operation_name="fetch test deed",
            operation=supabase.table("mortgage_deeds").select("id").limit(1).execute(),
            error_msg="Failed to fetch test deed"
        )
        
        if not deed_result.data:
            print("❌ No mortgage deeds found in database")
            return
        
        deed_id = deed_result.data[0]["id"]
        print(f"✅ Found deed ID: {deed_id}")
        
        # Get a borrower for this deed
        borrower_result = await handle_supabase_operation(
            operation_name="fetch test borrower",
            operation=supabase.table("borrowers").select("id, email").eq("deed_id", deed_id).limit(1).execute(),
            error_msg="Failed to fetch test borrower"
        )
        
        if not borrower_result.data:
            print("❌ No borrowers found for this deed")
            return
        
        borrower = borrower_result.data[0]
        print(f"✅ Found borrower: {borrower['email']}")
        
        # Create a test signing token
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
            print(f"✅ Successfully created test signing token: {token[:10]}...")
            test_token = token
        else:
            print("❌ Failed to create test signing token")
            return
            
    except Exception as e:
        print(f"❌ Error creating test signing token: {e}")
        return
    
    # Test 3: Test the signing page endpoint
    print("\n3. Testing signing page endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:8080/api/signing/sign/{test_token}")
            print(f"Signing page response status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Signing page loads successfully")
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    print("✅ Returns HTML content")
                    
                    # Check if the HTML contains the signing button
                    html_content = response.text
                    if "Signera Pantbrev Digitalt" in html_content:
                        print("✅ HTML contains signing button")
                    else:
                        print("❌ HTML missing signing button")
                        
                    if test_token in html_content:
                        print("✅ HTML contains the signing token")
                    else:
                        print("❌ HTML missing signing token")
                else:
                    print(f"❌ Unexpected content type: {content_type}")
            else:
                print(f"❌ Signing page failed: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error testing signing page: {e}")
    
    # Test 4: Test the signing API endpoint
    print("\n4. Testing signing API endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:8080/api/signing/sign",
                json={"token": test_token}
            )
            print(f"Signing API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Signing API works correctly")
                print(f"Response: {result}")
            else:
                print(f"❌ Signing API failed: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error testing signing API: {e}")
    
    # Test 5: Test the redirect route
    print("\n5. Testing redirect route...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:8080/sign/{test_token}")
            print(f"Redirect response status: {response.status_code}")
            
            if response.status_code == 307:
                print("✅ Redirect route working correctly")
                location = response.headers.get("location", "")
                if location:
                    print(f"Redirects to: {location}")
            else:
                print(f"❌ Unexpected redirect response: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error testing redirect: {e}")
    
    # Clean up test token
    print("\n6. Cleaning up test token...")
    try:
        await handle_supabase_operation(
            operation_name="delete test signing token",
            operation=supabase.table("signing_tokens").delete().eq("token", test_token).execute(),
            error_msg="Failed to delete test signing token"
        )
        print("✅ Test token cleaned up")
    except Exception as e:
        print(f"❌ Error cleaning up test token: {e}")

if __name__ == "__main__":
    asyncio.run(test_signing_flow())
    print("\nTest completed!") 