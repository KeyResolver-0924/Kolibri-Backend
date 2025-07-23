from dotenv import load_dotenv
import asyncio
import os
from typing import Optional, Dict, Any
from supabase import create_client as supabase_create_client, Client as SupabaseClient
from dataclasses import dataclass
import datetime

# Load environment variables from .env file
load_dotenv()

@dataclass
class SupabaseConfig:
    url: str = os.getenv("SUPABASE_URL", "")
    key: str = os.getenv("SUPABASE_KEY", "")

    def is_valid(self) -> bool:
        return bool(self.url and self.key)

class UserError(Exception):
    """Custom exception for user-related errors"""
    pass

def get_supabase_client() -> SupabaseClient:
    """Create and return a Supabase client using environment variables"""
    config = SupabaseConfig()
    if not config.is_valid():
        raise UserError("Missing Supabase configuration. Please check your .env file.")
    return supabase_create_client(config.url, config.key)

async def update_user_bank_id(supabase: SupabaseClient, bank_id: int) -> Dict[str, Any]:
    """Update the bank_id for an authenticated user"""
    # First update the user metadata
    update_data = {
        "data": {
            "bank_id": int(bank_id)
        }
    }
    user_update = supabase.auth.update_user(update_data)
    
    # Then explicitly set email verification
    admin_update = supabase.auth.admin.update_user_by_id(
        user_update.user.id,
        {"email_confirmed_at": datetime.datetime.now().isoformat()}
    )
    return admin_update

async def create_or_update_user(email: str, password: str, bank_id: str) -> None:
    """
    Create a new user or update an existing user's bank_id.
    
    Args:
        email: User's email address
        password: User's password
        bank_id: Bank ID to associate with the user
    
    Raises:
        UserError: If authentication fails or user creation/update fails
    """
    try:
        supabase = get_supabase_client()
        
        # Try to sign in first to check if user exists
        try:
            sign_in_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            if sign_in_response.user:
                # Update existing user's bank_id
                update_response = await update_user_bank_id(supabase, bank_id)
                print("User updated successfully:", update_response)
                return
        except Exception:
            # If sign-in fails, try to create new user
            user_data = {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "bank_id": int(bank_id)
                    }
                }
            }
            response = supabase.auth.sign_up(user_data)
            if response.user:
                # Explicitly verify email for new user
                admin_update = supabase.auth.admin.update_user_by_id(
                    response.user.id,
                    {"email_confirmed_at": datetime.datetime.now().isoformat()}
                )
                print("User created and verified successfully:", admin_update)
            else:
                raise UserError("Failed to create user")
            
    except UserError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

async def main() -> None:
    """Main function to handle user input and program flow"""
    email = input("Enter email: ")
    password = input("Enter password: ")
    bank_id = input("Enter bank ID: ")
    await create_or_update_user(email, password, bank_id)

if __name__ == "__main__":
    asyncio.run(main()) 