#!/usr/bin/env python3
"""
Debug script to check deed status and signing state
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from api.config import get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def debug_deed_status():
    """Debug the deed status and signing state."""
    
    print("🔍 Debugging Deed Status and Signing State")
    print("=" * 50)
    
    # Get Supabase client
    supabase = await get_supabase()
    
    try:
        # Get all mortgage deeds with their current status
        print("\n1. Checking all mortgage deeds...")
        
        deeds_result = await handle_supabase_operation(
            operation_name="fetch all deeds",
            operation=supabase.table("mortgage_deeds")
                .select("id, credit_number, status, apartment_number, apartment_address")
                .execute(),
            error_msg="Failed to fetch deeds"
        )
        
        if deeds_result.data:
            print(f"   Found {len(deeds_result.data)} mortgage deeds:")
            for deed in deeds_result.data:
                print(f"   - Deed ID: {deed['id']}, Status: {deed['status']}, Credit: {deed['credit_number']}, Apt: {deed['apartment_number']}")
        else:
            print("   No mortgage deeds found")
            return
        
        # Get the most recent deed for detailed analysis
        latest_deed = deeds_result.data[-1]
        deed_id = latest_deed["id"]
        
        print(f"\n2. Analyzing latest deed (ID: {deed_id})...")
        print(f"   Current status: {latest_deed['status']}")
        
        # Check borrowers for this deed
        print("\n3. Checking borrowers...")
        borrowers_result = await handle_supabase_operation(
            operation_name="fetch borrowers for deed",
            operation=supabase.table("borrowers")
                .select("id, name, email, signature_timestamp")
                .eq("deed_id", deed_id)
                .execute(),
            error_msg="Failed to fetch borrowers"
        )
        
        if borrowers_result.data:
            print(f"   Found {len(borrowers_result.data)} borrowers:")
            signed_borrowers = 0
            for borrower in borrowers_result.data:
                status = "✅ Signed" if borrower["signature_timestamp"] else "⏳ Pending"
                print(f"   - {borrower['name']} ({borrower['email']}): {status}")
                if borrower["signature_timestamp"]:
                    signed_borrowers += 1
            
            print(f"   Borrower signing progress: {signed_borrowers}/{len(borrowers_result.data)}")
        else:
            print("   No borrowers found for this deed")
        
        # Check housing cooperative signers for this deed
        print("\n4. Checking housing cooperative signers...")
        signers_result = await handle_supabase_operation(
            operation_name="fetch signers for deed",
            operation=supabase.table("housing_cooperative_signers")
                .select("id, administrator_name, administrator_email, signature_timestamp")
                .eq("mortgage_deed_id", deed_id)
                .execute(),
            error_msg="Failed to fetch signers"
        )
        
        if signers_result.data:
            print(f"   Found {len(signers_result.data)} housing cooperative signers:")
            signed_signers = 0
            for signer in signers_result.data:
                status = "✅ Signed" if signer["signature_timestamp"] else "⏳ Pending"
                print(f"   - {signer['administrator_name']} ({signer['administrator_email']}): {status}")
                if signer["signature_timestamp"]:
                    signed_signers += 1
            
            print(f"   Signer signing progress: {signed_signers}/{len(signers_result.data)}")
        else:
            print("   No housing cooperative signers found for this deed")
        
        # Check signing tokens for this deed
        print("\n5. Checking signing tokens...")
        tokens_result = await handle_supabase_operation(
            operation_name="fetch tokens for deed",
            operation=supabase.table("signing_tokens")
                .select("id, signer_type, borrower_id, housing_cooperative_signer_id, email, used_at")
                .eq("deed_id", deed_id)
                .execute(),
            error_msg="Failed to fetch signing tokens"
        )
        
        if tokens_result.data:
            print(f"   Found {len(tokens_result.data)} signing tokens:")
            for token in tokens_result.data:
                used_status = "✅ Used" if token["used_at"] else "⏳ Unused"
                print(f"   - {token['signer_type']} ({token['email']}): {used_status}")
        else:
            print("   No signing tokens found for this deed")
        
        # Determine expected status
        print("\n6. Expected status analysis...")
        
        if borrowers_result.data and signers_result.data:
            all_borrowers_signed = all(b["signature_timestamp"] for b in borrowers_result.data)
            all_signers_signed = all(s["signature_timestamp"] for s in signers_result.data)
            
            if all_borrowers_signed and all_signers_signed:
                expected_status = "COMPLETED"
                print(f"   ✅ All borrowers and signers have signed - Status should be: {expected_status}")
            elif all_borrowers_signed:
                expected_status = "PENDING_HOUSING_COOPERATIVE_SIGNATURE"
                print(f"   ⏳ All borrowers signed, waiting for signers - Status should be: {expected_status}")
            else:
                expected_status = "PENDING_BORROWER_SIGNATURE"
                print(f"   ⏳ Waiting for borrowers to sign - Status should be: {expected_status}")
            
            if latest_deed["status"] != expected_status:
                print(f"   ❌ Status mismatch! Current: {latest_deed['status']}, Expected: {expected_status}")
            else:
                print(f"   ✅ Status is correct: {latest_deed['status']}")
        
        print("\n✅ Debug analysis completed!")
        
    except Exception as e:
        print(f"\n❌ Debug failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(debug_deed_status()) 