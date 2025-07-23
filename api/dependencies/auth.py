from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase._async.client import AsyncClient as SupabaseClient
from typing import Optional
from api.config import get_supabase
import sys

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: SupabaseClient = Depends(get_supabase)
) -> dict:
    """
    Validate the JWT token and return the user information.
    This dependency will be used to protect routes that require authentication.
    """
    try:
        print(f"Validating token: {credentials.credentials[:50]}...")
        # Verify the JWT token using Supabase
        user_response = await supabase.auth.get_user(credentials.credentials)
        
        # print(f"User response: {user_response}")
        if not user_response or not user_response.user:
            print("No user found in response")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Convert User object to dict with all necessary attributes
        user = user_response.user
        return {
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "user_metadata": user.user_metadata or {},
            "app_metadata": user.app_metadata or {},
            "aud": user.aud,
            "role": user.role,
            "bank_id": user.user_metadata.get("bank_id")
        }
                
    except Exception as e:
        print(f"Auth error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    supabase: SupabaseClient = Depends(get_supabase)
) -> Optional[dict]:
    """
    Similar to get_current_user but doesn't raise an exception if no token is provided.
    Useful for routes that can work with or without authentication.
    """
    if not credentials:
        return None
    
    try:
        user_response = await supabase.auth.get_user(credentials.credentials)
        if not user_response or not user_response.user:
            return None
            
        user = user_response.user
        return {
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "user_metadata": user.user_metadata or {},
            "app_metadata": user.app_metadata or {},
            "aud": user.aud,
            "role": user.role,
            "bank_id": user.user_metadata.get("bank_id")
        }
    except:
        return None 