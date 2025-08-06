#!/usr/bin/env python3
"""
Comprehensive test for complete signing flow including housing cooperative signers
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

async def test_complete_signing_flow():
    """Test the complete signing flow including housing cooperative signers."""
    
    print("Testing Complete Signing Flow (Borrowers + Housing Cooperative)")
    print("=" * 60)
    
    try:
        supabase = await get_supabase()
        
        # Test 1: Find a deed with both borrowers and housing cooperative signers
        print("\n1. Finding deed with borrowers and housing cooperative signers...")
        deed_result = await handle_supabase_operation(
            operation_name="fetch deed with all signers",
            operation=supabase.table("mortgage_deeds")
                .select("id, credit_number, apartment_number, status")
                .limit(1)
                .execute(),
            error_msg="Failed to fetch test deed"
        )
        
        if not deed_result.data:
            print("❌ No mortgage deeds found")
            return
        
        deed_id = deed_result.data[0]["id"]
        deed_status = deed_result.data[0]["status"]
        print(f"✅ Found deed ID: {deed_id}, Status: {deed_status}")
        
        # Test 2: Check borrowers
        print("\n2. Checking borrowers...")
        borrowers_result = await handle_supabase_operation(
            operation_name="fetch borrowers",
            operation=supabase.table("borrowers")
                .select("*")
                .eq("deed_id", deed_id)
                .execute(),
            error_msg="Failed to fetch borrowers"
        )
        
        if borrowers_result.data:
            print(f"✅ Found {len(borrowers_result.data)} borrowers")
            for borrower in borrowers_result.data:
                print(f"   - {borrower['name']} ({borrower['email']})")
                if borrower.get('signature_timestamp'):
                    print(f"     ✅ Already signed at {borrower['signature_timestamp']}")
                else:
                    print(f"     ⏳ Not signed yet")
        else:
            print("❌ No borrowers found for this deed")
        
        # Test 3: Check housing cooperative signers
        print("\n3. Checking housing cooperative signers...")
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
        
        # Test 4: Create test signing tokens
        print("\n4. Creating test signing tokens...")
        
        # Create borrower token
        if borrowers_result.data:
            borrower = borrowers_result.data[0]
            borrower_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=7)
            
            borrower_token_data = {
                "deed_id": deed_id,
                "borrower_id": borrower["id"],
                "token": borrower_token,
                "email": borrower["email"],
                "expires_at": expires_at.isoformat()
            }
            
            await handle_supabase_operation(
                operation_name="create borrower test token",
                operation=supabase.table("signing_tokens").insert(borrower_token_data).execute(),
                error_msg="Failed to create borrower test token"
            )
            print(f"✅ Created borrower token: {borrower_token[:10]}...")
        
        # Create housing cooperative signer token
        if signers_result.data:
            signer = signers_result.data[0]
            signer_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=7)
            
            signer_token_data = {
                "deed_id": deed_id,
                "token": signer_token,
                "email": signer["administrator_email"],
                "expires_at": expires_at.isoformat()
            }
            
            await handle_supabase_operation(
                operation_name="create signer test token",
                operation=supabase.table("signing_tokens").insert(signer_token_data).execute(),
                error_msg="Failed to create signer test token"
            )
            print(f"✅ Created housing cooperative signer token: {signer_token[:10]}...")
        
        # Test 5: Test signing flow
        print("\n5. Testing signing flow...")
        
        # Test borrower signing
        if borrowers_result.data and 'borrower_token' in locals():
            print(f"   Testing borrower signing with token: {borrower_token[:10]}...")
            # This would normally be a POST request to /api/signing/sign
            # For now, we'll just simulate the database updates
            
            # Update borrower signature
            await handle_supabase_operation(
                operation_name="update borrower signature for test",
                operation=supabase.table("borrowers")
                    .update({"signature_timestamp": datetime.now().isoformat()})
                    .eq("id", borrower["id"])
                    .execute(),
                error_msg="Failed to update borrower signature"
            )
            print("   ✅ Borrower signature updated")
        
        # Test housing cooperative signer signing
        if signers_result.data and 'signer_token' in locals():
            print(f"   Testing housing cooperative signer signing with token: {signer_token[:10]}...")
            
            # Update housing cooperative signer signature
            await handle_supabase_operation(
                operation_name="update signer signature for test",
                operation=supabase.table("housing_cooperative_signers")
                    .update({"signature_timestamp": datetime.now().isoformat()})
                    .eq("id", signer["id"])
                    .execute(),
                error_msg="Failed to update signer signature"
            )
            print("   ✅ Housing cooperative signer signature updated")
        
        # Test 6: Check final status
        print("\n6. Checking final status...")
        
        # Check borrower signatures
        final_borrowers = await handle_supabase_operation(
            operation_name="fetch final borrowers",
            operation=supabase.table("borrowers")
                .select("name, signature_timestamp")
                .eq("deed_id", deed_id)
                .execute(),
            error_msg="Failed to fetch final borrowers"
        )
        
        if final_borrowers.data:
            print("   Borrower signatures:")
            for borrower in final_borrowers.data:
                if borrower.get('signature_timestamp'):
                    print(f"     ✅ {borrower['name']} - Signed at {borrower['signature_timestamp']}")
                else:
                    print(f"     ⏳ {borrower['name']} - Not signed")
        
        # Check housing cooperative signer signatures
        final_signers = await handle_supabase_operation(
            operation_name="fetch final signers",
            operation=supabase.table("housing_cooperative_signers")
                .select("administrator_name, signature_timestamp")
                .eq("mortgage_deed_id", deed_id)
                .execute(),
            error_msg="Failed to fetch final signers"
        )
        
        if final_signers.data:
            print("   Housing cooperative signer signatures:")
            for signer in final_signers.data:
                if signer.get('signature_timestamp'):
                    print(f"     ✅ {signer['administrator_name']} - Signed at {signer['signature_timestamp']}")
                else:
                    print(f"     ⏳ {signer['administrator_name']} - Not signed")
        
        # Clean up test tokens
        print("\n7. Cleaning up test tokens...")
        if 'borrower_token' in locals():
            await handle_supabase_operation(
                operation_name="delete borrower test token",
                operation=supabase.table("signing_tokens").delete().eq("token", borrower_token).execute(),
                error_msg="Failed to delete borrower test token"
            )
            print("   ✅ Cleaned up borrower test token")
        
        if 'signer_token' in locals():
            await handle_supabase_operation(
                operation_name="delete signer test token",
                operation=supabase.table("signing_tokens").delete().eq("token", signer_token).execute(),
                error_msg="Failed to delete signer test token"
            )
            print("   ✅ Cleaned up housing cooperative signer test token")
            
    except Exception as e:
        print(f"❌ Error in test: {e}")

if __name__ == "__main__":
    asyncio.run(test_complete_signing_flow())
    print("\nTest completed!") 