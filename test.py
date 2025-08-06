import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from api.config import get_settings
from api.utils.supabase_utils import handle_supabase_operation
from supabase import create_client, Client

async def test_backend():
    """Test the backend configuration and basic functionality."""
    try:
        print("Testing backend configuration...")
        
        # Test settings
        settings = get_settings()
        print(f"✅ Settings loaded successfully")
        print(f"   Supabase URL: {settings.SUPABASE_URL}")
        print(f"   CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
        print(f"   Environment: {settings.ENVIRONMENT}")
        
        # Test Supabase connection
        print("\nTesting Supabase connection...")
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Test a simple query
        result = await handle_supabase_operation(
            operation_name="test connection",
            operation=supabase.table("mortgage_deeds").select("id").limit(1).execute(),
            error_msg="Failed to connect to Supabase"
        )
        print("✅ Supabase connection successful")
        
        # Test environment variables
        print("\nTesting environment variables...")
        required_vars = [
            "SUPABASE_URL",
            "SUPABASE_KEY", 
            "MAILGUN_API_KEY",
            "MAILGUN_DOMAIN",
            "EMAILS_FROM_EMAIL",
            "EMAILS_FROM_NAME",
            "FRONTEND_URL",
            "BACKEND_URL"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(settings, var, None):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
        else:
            print("✅ All required environment variables are set")
        
        print("\n✅ Backend test completed successfully!")
        
    except Exception as e:
        print(f"❌ Backend test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backend())
