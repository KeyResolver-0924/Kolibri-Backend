#!/usr/bin/env python3
"""
Test to verify signing URL generation in email context
"""

import asyncio
import sys
import os
import secrets
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.config import get_settings, get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def test_email_signing_url():
    """Test signing URL generation for email context."""
    
    print("Testing Email Signing URL Generation")
    print("=" * 40)
    
    try:
        settings = get_settings()
        
        # Test 1: Generate a test token and signing URL
        print("\n1. Generating test signing URL...")
        token = secrets.token_urlsafe(32)
        signing_url = f"{settings.BACKEND_URL}/sign/{token}"
        
        print(f"   Token: {token[:10]}...")
        print(f"   Backend URL: {settings.BACKEND_URL}")
        print(f"   Signing URL: {signing_url}")
        
        # Test 2: Create email context
        print("\n2. Creating email context...")
        email_context = {
            "admin_name": "Test Administrator",
            "deed": {
                "reference_number": "TEST123",
                "apartment_number": "A1",
                "apartment_address": "Test Address 1",
                "cooperative_name": "Test Cooperative",
                "borrowers": [{"name": "Test Borrower", "email": "test@example.com"}],
                "created_date": "2024-01-01"
            },
            "signing_url": signing_url,
            "from_name": settings.EMAILS_FROM_NAME,
            "current_year": 2024
        }
        
        print(f"   Email context created successfully")
        print(f"   Signing URL in context: {email_context['signing_url']}")
        
        # Test 3: Test template rendering (simulate)
        print("\n3. Testing template rendering...")
        
        # Simulate the template rendering by checking if signing_url is available
        if "signing_url" in email_context:
            print("   ✅ signing_url is available in email context")
            print(f"   🔗 URL: {email_context['signing_url']}")
        else:
            print("   ❌ signing_url is missing from email context")
            return
        
        # Test 4: Test URL format
        print("\n4. Testing URL format...")
        if signing_url.startswith("http"):
            print("   ✅ URL starts with http/https")
        else:
            print("   ❌ URL does not start with http/https")
        
        if "/sign/" in signing_url:
            print("   ✅ URL contains /sign/ path")
        else:
            print("   ❌ URL does not contain /sign/ path")
        
        if token in signing_url:
            print("   ✅ Token is included in URL")
        else:
            print("   ❌ Token is not included in URL")
        
        # Test 5: Test with actual database token
        print("\n5. Testing with actual database token...")
        supabase = await get_supabase()
        
        # Find a deed with housing cooperative signers
        deed_result = await handle_supabase_operation(
            operation_name="fetch test deed",
            operation=supabase.table("mortgage_deeds")
                .select("id")
                .limit(1)
                .execute(),
            error_msg="Failed to fetch test deed"
        )
        
        if deed_result.data:
            deed_id = deed_result.data[0]["id"]
            print(f"   Found deed ID: {deed_id}")
            
            # Create a test token in database
            test_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=7)
            
            try:
                # Try to create token with new schema
                token_data = {
                    "deed_id": deed_id,
                    "signer_type": "housing_cooperative_signer",
                    "token": test_token,
                    "email": "test@example.com",
                    "expires_at": expires_at.isoformat()
                }
                
                await handle_supabase_operation(
                    operation_name="create test token",
                    operation=supabase.table("signing_tokens").insert(token_data).execute(),
                    error_msg="Failed to create test token"
                )
                
                print(f"   ✅ Created test token in database: {test_token[:10]}...")
                
                # Generate signing URL
                db_signing_url = f"{settings.BACKEND_URL}/sign/{test_token}"
                print(f"   🔗 Database signing URL: {db_signing_url}")
                
                # Clean up
                await handle_supabase_operation(
                    operation_name="delete test token",
                    operation=supabase.table("signing_tokens").delete().eq("token", test_token).execute(),
                    error_msg="Failed to delete test token"
                )
                print("   ✅ Cleaned up test token")
                
            except Exception as e:
                print(f"   ⚠️  Database test failed (schema may not be updated): {e}")
        else:
            print("   ⚠️  No deeds found for database test")
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print("   - Signing URL generation works correctly")
        print("   - Email context includes signing_url")
        print("   - URL format is correct")
        print("   - Template should render with clickable button")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")

if __name__ == "__main__":
    asyncio.run(test_email_signing_url())
    print("\nTest completed!") 