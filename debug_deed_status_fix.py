#!/usr/bin/env python3
"""
Debug script to check and fix deed status issues
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from api.config import get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def debug_and_fix_deed_status():
    """Debug and fix deed status issues."""
    
    print("🔍 Debugging and Fixing Deed Status Issues")
    print("=" * 50)
    
    # Get Supabase client
    supabase = await get_supabase()
    
    try:
        # Get all mortgage deeds with their current status
        print("\n1. Checking all mortgage deeds...")
        
        deeds_result = await handle_supabase_operation(
            operation_name="fetch all deeds",
            operation=supabase.table("mortgage_deeds")
                .select("id, status, created_at, apartment_address")
                .order("created_at", ascending=False)
                .execute(),
            error_msg="Failed to fetch mortgage deeds"
        )
        
        print(f"Found {len(deeds_result.data)} mortgage deeds")
        
        for deed in deeds_result.data:
            print(f"\n--- Deed ID: {deed['id']} ---")
            print(f"Status: {deed['status']}")
            print(f"Address: {deed['apartment_address']}")
            
            # Check borrowers
            borrowers_result = await handle_supabase_operation(
                operation_name="fetch borrowers for deed",
                operation=supabase.table("borrowers")
                    .select("id, name, email, signature_timestamp")
                    .eq("mortgage_deed_id", deed['id'])
                    .execute(),
                error_msg="Failed to fetch borrowers"
            )
            
            print(f"Borrowers: {len(borrowers_result.data)}")
            signed_borrowers = sum(1 for b in borrowers_result.data if b['signature_timestamp'])
            print(f"Signed borrowers: {signed_borrowers}/{len(borrowers_result.data)}")
            
            # Check housing cooperative signers
            signers_result = await handle_supabase_operation(
                operation_name="fetch housing cooperative signers for deed",
                operation=supabase.table("housing_cooperative_signers")
                    .select("id, administrator_name, administrator_email, signature_timestamp")
                    .eq("mortgage_deed_id", deed['id'])
                    .execute(),
                error_msg="Failed to fetch housing cooperative signers"
            )
            
            print(f"Housing Cooperative Signers: {len(signers_result.data)}")
            signed_signers = sum(1 for s in signers_result.data if s['signature_timestamp'])
            print(f"Signed signers: {signed_signers}/{len(signers_result.data)}")
            
            # Determine what the status should be
            total_borrowers = len(borrowers_result.data)
            total_signers = len(signers_result.data)
            
            if total_borrowers == 0 or total_signers == 0:
                print("⚠️  Warning: No borrowers or signers found")
                continue
            
            # Check if all borrowers have signed
            all_borrowers_signed = signed_borrowers == total_borrowers
            all_signers_signed = signed_signers == total_signers
            
            print(f"All borrowers signed: {all_borrowers_signed}")
            print(f"All signers signed: {all_signers_signed}")
            
            # Determine correct status
            correct_status = None
            if not all_borrowers_signed:
                correct_status = "PENDING_BORROWER_SIGNATURE"
            elif not all_signers_signed:
                correct_status = "PENDING_HOUSING_COOPERATIVE_SIGNATURE"
            else:
                correct_status = "COMPLETED"
            
            print(f"Current status: {deed['status']}")
            print(f"Correct status: {correct_status}")
            
            # Fix status if incorrect
            if deed['status'] != correct_status:
                print(f"🔧 Fixing status from '{deed['status']}' to '{correct_status}'")
                
                await handle_supabase_operation(
                    operation_name="update deed status",
                    operation=supabase.table("mortgage_deeds")
                        .update({"status": correct_status})
                        .eq("id", deed['id'])
                        .execute(),
                    error_msg="Failed to update deed status"
                )
                
                print(f"✅ Status updated successfully")
            else:
                print("✅ Status is correct")
        
        print("\n🎉 Debug and fix completed!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_and_fix_deed_status()) 