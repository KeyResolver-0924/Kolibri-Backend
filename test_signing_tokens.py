#!/usr/bin/env python3
"""
Test script to check signing_tokens table accessibility.
This script can be run to test if the signing_tokens table exists and is accessible.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from api.config import get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def test_signing_tokens_table():
    """Test if the signing_tokens table exists and is accessible."""
    
    print("Testing signing_tokens table accessibility...")
    
    # Get Supabase client
    supabase = await get_supabase()
    
    # Test 1: Check if table exists by trying to select from it
    print("\n1. Testing if signing_tokens table exists...")
    try:
        result = await handle_supabase_operation(
            operation_name="check signing_tokens table",
            operation=supabase.table("signing_tokens").select("id").limit(1).execute(),
            error_msg="Failed to access signing_tokens table"
        )
        print(f"✓ signing_tokens table exists and is accessible")
        print(f"  Found {len(result.data)} records")
    except Exception as e:
        print(f"✗ Failed to access signing_tokens table: {e}")
        return False
    
    # Test 2: Try to insert a test record
    print("\n2. Testing signing_tokens table insert...")
    try:
        test_data = {
            "deed_id": 1,  # Use a test deed ID
            "borrower_id": 1,  # Use a test borrower ID
            "token": "test_token_123",
            "email": "test@example.com",
            "expires_at": "2025-12-31T23:59:59"
        }
        
        result = await handle_supabase_operation(
            operation_name="insert test signing token",
            operation=supabase.table("signing_tokens").insert(test_data).execute(),
            error_msg="Failed to insert test signing token"
        )
        print(f"✓ Successfully inserted test signing token")
        print(f"  Inserted record ID: {result.data[0]['id'] if result.data else 'Unknown'}")
        
        # Clean up: Delete the test record
        if result.data:
            test_id = result.data[0]['id']
            await handle_supabase_operation(
                operation_name="delete test signing token",
                operation=supabase.table("signing_tokens").delete().eq("id", test_id).execute(),
                error_msg="Failed to delete test signing token"
            )
            print(f"✓ Cleaned up test record")
            
    except Exception as e:
        print(f"✗ Failed to insert test signing token: {e}")
        return False
    
    print("\n✓ All tests passed!")
    return True

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_signing_tokens_table())
    sys.exit(0 if success else 1) 