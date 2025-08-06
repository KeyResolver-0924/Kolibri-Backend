#!/usr/bin/env python3
"""
Test script for housing cooperative signing functionality
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.config import get_settings, get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def test_housing_cooperative_signing():
    """Test housing cooperative signing functionality."""
    
    print("Testing Housing Cooperative Signing")
    print("=" * 40)
    
    try:
        supabase = await get_supabase()
        
        # Test 1: Check if housing cooperative signers table exists
        print("\n1. Checking housing_cooperative_signers table...")
        try:
            result = await handle_supabase_operation(
                operation_name="check housing cooperative signers table",
                operation=supabase.table("housing_cooperative_signers").select("id").limit(1).execute(),
                error_msg="Failed to access housing_cooperative_signers table"
            )
            print("✅ housing_cooperative_signers table exists and is accessible")
        except Exception as e:
            print(f"❌ Error accessing housing_cooperative_signers table: {e}")
            return
        
        # Test 2: Check if we can find a deed with housing cooperative signers
        print("\n2. Finding deed with housing cooperative signers...")
        deed_result = await handle_supabase_operation(
            operation_name="fetch deed with housing cooperative signers",
            operation=supabase.table("mortgage_deeds")
                .select("id, credit_number, apartment_number")
                .limit(1)
                .execute(),
            error_msg="Failed to fetch test deed"
        )
        
        if not deed_result.data:
            print("❌ No mortgage deeds found")
            return
        
        deed_id = deed_result.data[0]["id"]
        print(f"✅ Found deed ID: {deed_id}")
        
        # Test 3: Check housing cooperative signers for this deed
        signers_result = await handle_supabase_operation(
            operation_name="fetch housing cooperative signers",
            operation=supabase.table("housing_cooperative_signers")
                .select("*")
                .eq("mortgage_deed_id", deed_id)
                .execute(),
            error_msg="Failed to fetch housing cooperative signers"
        )
        
        if signers_result.data:
            print(f"✅ Found {len(signers_result.data)} housing cooperative signers")
            for signer in signers_result.data:
                print(f"   - {signer['administrator_name']} ({signer['administrator_email']})")
                if signer.get('signature_timestamp'):
                    print(f"     ✅ Already signed at {signer['signature_timestamp']}")
                else:
                    print(f"     ⏳ Not signed yet")
        else:
            print("❌ No housing cooperative signers found for this deed")
        
        # Test 4: Check current deed status
        deed_status_result = await handle_supabase_operation(
            operation_name="fetch deed status",
            operation=supabase.table("mortgage_deeds")
                .select("status")
                .eq("id", deed_id)
                .single()
                .execute(),
            error_msg="Failed to fetch deed status"
        )
        
        if deed_status_result.data:
            status = deed_status_result.data["status"]
            print(f"✅ Current deed status: {status}")
        else:
            print("❌ Could not fetch deed status")
            
    except Exception as e:
        print(f"❌ Error in test: {e}")

if __name__ == "__main__":
    asyncio.run(test_housing_cooperative_signing())
    print("\nTest completed!") 