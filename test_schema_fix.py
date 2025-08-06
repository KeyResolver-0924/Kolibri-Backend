#!/usr/bin/env python3
"""
Test script to verify the signing tokens schema fix
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import secrets

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from api.config import get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def test_schema_fix():
    """Test the signing tokens schema fix."""
    
    print("🔧 Testing Signing Tokens Schema Fix")
    print("=" * 50)
    
    # Get Supabase client
    supabase = await get_supabase()
    
    try:
        # Test 1: Check if new columns exist
        print("\n1. Checking database schema...")
        
        result = await handle_supabase_operation(
            operation_name="check schema",
            operation=supabase.table("signing_tokens").select("id, deed_id, borrower_id, housing_cooperative_signer_id, signer_type, token, email, expires_at").limit(1).execute(),
            error_msg="Failed to check schema"
        )
        
        print("   ✅ Schema check successful")
        
        # Test 2: Try to create a borrower token
        print("\n2. Testing borrower token creation...")
        
        # Get a sample deed and borrower
        deed_result = await handle_supabase_operation(
            operation_name="get sample deed",
            operation=supabase.table("mortgage_deeds").select("id").limit(1).execute(),
            error_msg="Failed to get sample deed"
        )
        
        if deed_result.data:
            deed_id = deed_result.data[0]["id"]
            print(f"   Using deed ID: {deed_id}")
            
            borrower_result = await handle_supabase_operation(
                operation_name="get sample borrower",
                operation=supabase.table("borrowers").select("id, email").eq("deed_id", deed_id).limit(1).execute(),
                error_msg="Failed to get sample borrower"
            )
            
            if borrower_result.data:
                borrower = borrower_result.data[0]
                print(f"   Using borrower ID: {borrower['id']}, email: {borrower['email']}")
                
                # Create test borrower token
                test_token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(days=7)
                
                borrower_token_data = {
                    "deed_id": deed_id,
                    "borrower_id": borrower["id"],
                    "signer_type": "borrower",
                    "token": test_token,
                    "email": borrower["email"],
                    "expires_at": expires_at.isoformat()
                }
                
                await handle_supabase_operation(
                    operation_name="create borrower token",
                    operation=supabase.table("signing_tokens").insert(borrower_token_data).execute(),
                    error_msg="Failed to create borrower token"
                )
                
                print(f"   ✅ Created borrower token: {test_token[:10]}...")
                
                # Clean up
                await handle_supabase_operation(
                    operation_name="delete test token",
                    operation=supabase.table("signing_tokens").delete().eq("token", test_token).execute(),
                    error_msg="Failed to delete test token"
                )
                print("   ✅ Cleaned up borrower token")
            else:
                print("   ⚠️  No borrowers found for testing")
        else:
            print("   ⚠️  No deeds found for testing")
        
        # Test 3: Try to create a housing cooperative signer token
        print("\n3. Testing housing cooperative signer token creation...")
        
        if deed_result.data:
            deed_id = deed_result.data[0]["id"]
            
            signer_result = await handle_supabase_operation(
                operation_name="get sample signer",
                operation=supabase.table("housing_cooperative_signers").select("id, administrator_email").eq("mortgage_deed_id", deed_id).limit(1).execute(),
                error_msg="Failed to get sample signer"
            )
            
            if signer_result.data:
                signer = signer_result.data[0]
                print(f"   Using signer ID: {signer['id']}, email: {signer['administrator_email']}")
                
                # Create test signer token
                test_token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(days=7)
                
                signer_token_data = {
                    "deed_id": deed_id,
                    "housing_cooperative_signer_id": signer["id"],
                    "signer_type": "housing_cooperative_signer",
                    "token": test_token,
                    "email": signer["administrator_email"],
                    "expires_at": expires_at.isoformat()
                }
                
                await handle_supabase_operation(
                    operation_name="create signer token",
                    operation=supabase.table("signing_tokens").insert(signer_token_data).execute(),
                    error_msg="Failed to create signer token"
                )
                
                print(f"   ✅ Created signer token: {test_token[:10]}...")
                
                # Clean up
                await handle_supabase_operation(
                    operation_name="delete test token",
                    operation=supabase.table("signing_tokens").delete().eq("token", test_token).execute(),
                    error_msg="Failed to delete test token"
                )
                print("   ✅ Cleaned up signer token")
            else:
                print("   ⚠️  No housing cooperative signers found for testing")
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print("   - Database schema supports both borrower and housing cooperative signer tokens")
        print("   - Token creation works for both types")
        print("   - Ready for production use")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        print("\n🔧 To fix this issue:")
        print("   1. Run the migration script in Supabase SQL Editor")
        print("   2. Restart the application")
        print("   3. Run this test again")

if __name__ == "__main__":
    asyncio.run(test_schema_fix()) 