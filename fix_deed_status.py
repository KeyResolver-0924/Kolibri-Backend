#!/usr/bin/env python3
"""
Script to manually fix deed status if needed
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from api.config import get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def fix_deed_status():
    """Fix deed status based on current signing state."""
    
    print("🔧 Fixing Deed Status")
    print("=" * 30)
    
    # Get Supabase client
    supabase = await get_supabase()
    
    try:
        # Get all mortgage deeds
        print("\n1. Fetching all mortgage deeds...")
        
        deeds_result = await handle_supabase_operation(
            operation_name="fetch all deeds",
            operation=supabase.table("mortgage_deeds")
                .select("id, credit_number, status, apartment_number")
                .execute(),
            error_msg="Failed to fetch deeds"
        )
        
        if not deeds_result.data:
            print("   No mortgage deeds found")
            return
        
        print(f"   Found {len(deeds_result.data)} mortgage deeds")
        
        # Process each deed
        for deed in deeds_result.data:
            deed_id = deed["id"]
            current_status = deed["status"]
            
            print(f"\n2. Processing deed ID {deed_id} (Credit: {deed['credit_number']}, Apt: {deed['apartment_number']})")
            print(f"   Current status: {current_status}")
            
            # Check borrowers
            borrowers_result = await handle_supabase_operation(
                operation_name="fetch borrowers for deed",
                operation=supabase.table("borrowers")
                    .select("signature_timestamp")
                    .eq("deed_id", deed_id)
                    .execute(),
                error_msg="Failed to fetch borrowers"
            )
            
            # Check housing cooperative signers
            signers_result = await handle_supabase_operation(
                operation_name="fetch signers for deed",
                operation=supabase.table("housing_cooperative_signers")
                    .select("signature_timestamp")
                    .eq("mortgage_deed_id", deed_id)
                    .execute(),
                error_msg="Failed to fetch signers"
            )
            
            # Calculate signing status
            all_borrowers_signed = False
            all_signers_signed = False
            
            if borrowers_result.data:
                all_borrowers_signed = all(b["signature_timestamp"] for b in borrowers_result.data)
                signed_borrowers = sum(1 for b in borrowers_result.data if b["signature_timestamp"])
                print(f"   Borrowers: {signed_borrowers}/{len(borrowers_result.data)} signed")
            
            if signers_result.data:
                all_signers_signed = all(s["signature_timestamp"] for s in signers_result.data)
                signed_signers = sum(1 for s in signers_result.data if s["signature_timestamp"])
                print(f"   Signers: {signed_signers}/{len(signers_result.data)} signed")
            
            # Determine correct status
            if all_borrowers_signed and all_signers_signed:
                correct_status = "COMPLETED"
            elif all_borrowers_signed:
                correct_status = "PENDING_HOUSING_COOPERATIVE_SIGNATURE"
            else:
                correct_status = "PENDING_BORROWER_SIGNATURE"
            
            print(f"   Expected status: {correct_status}")
            
            # Update status if needed
            if current_status != correct_status:
                print(f"   🔧 Updating status from '{current_status}' to '{correct_status}'")
                
                await handle_supabase_operation(
                    operation_name="update deed status",
                    operation=supabase.table("mortgage_deeds")
                        .update({"status": correct_status})
                        .eq("id", deed_id)
                        .execute(),
                    error_msg="Failed to update deed status"
                )
                
                print(f"   ✅ Status updated successfully")
            else:
                print(f"   ✅ Status is already correct")
        
        print("\n✅ All deed statuses have been checked and updated!")
        
    except Exception as e:
        print(f"\n❌ Fix failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(fix_deed_status()) 