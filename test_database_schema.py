#!/usr/bin/env python3
"""
Test to check current database schema and identify issues
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

async def test_database_schema():
    """Test current database schema and identify issues."""
    
    print("Testing Database Schema")
    print("=" * 25)
    
    try:
        supabase = await get_supabase()
        
        # Test 1: Check if signing_tokens table exists
        print("\n1. Checking signing_tokens table...")
        try:
            result = await handle_supabase_operation(
                operation_name="check signing_tokens table",
                operation=supabase.table("signing_tokens").select("id").limit(1).execute(),
                error_msg="Failed to access signing_tokens table"
            )
            print("   ✅ signing_tokens table exists")
        except Exception as e:
            print(f"   ❌ signing_tokens table error: {e}")
            return
        
        # Test 2: Check table structure
        print("\n2. Checking table structure...")
        try:
            # Check if signer_type column exists
            result = await handle_supabase_operation(
                operation_name="check signer_type column",
                operation=supabase.table("signing_tokens").select("signer_type").limit(1).execute(),
                error_msg="Failed to check signer_type column"
            )
            print("   ✅ signer_type column exists")
        except Exception as e:
            print(f"   ❌ signer_type column missing: {e}")
            print("   ⚠️  Database migration needed: update_signing_tokens_schema.sql")
            return
        
        # Test 3: Try to create a test token
        print("\n3. Testing token creation...")
        
        # Find a test deed
        deed_result = await handle_supabase_operation(
            operation_name="fetch test deed",
            operation=supabase.table("mortgage_deeds").select("id").limit(1).execute(),
            error_msg="Failed to fetch test deed"
        )
        
        if not deed_result.data:
            print("   ❌ No mortgage deeds found")
            return
        
        deed_id = deed_result.data[0]["id"]
        print(f"   Found deed ID: {deed_id}")
        
        # Try to create a test token
        test_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)
        
        token_data = {
            "deed_id": deed_id,
            "borrower_id": 1,
            "signer_type": "borrower",
            "token": test_token,
            "email": "test@example.com",
            "expires_at": expires_at.isoformat()
        }
        
        try:
            await handle_supabase_operation(
                operation_name="create test token",
                operation=supabase.table("signing_tokens").insert(token_data).execute(),
                error_msg="Failed to create test token"
            )
            print("   ✅ Test token created successfully")
            
            # Clean up
            await handle_supabase_operation(
                operation_name="delete test token",
                operation=supabase.table("signing_tokens").delete().eq("token", test_token).execute(),
                error_msg="Failed to delete test token"
            )
            print("   ✅ Test token cleaned up")
            
        except Exception as e:
            print(f"   ❌ Token creation failed: {e}")
        
        print("\n✅ Database schema test completed!")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")

if __name__ == "__main__":
    asyncio.run(test_database_schema())
    print("\nTest completed!") 