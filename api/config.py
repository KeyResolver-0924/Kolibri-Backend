from functools import lru_cache
from pydantic import BaseSettings, validator
from typing import List, Any, Union, Optional
from supabase._async.client import AsyncClient as SupabaseClient, create_client
from dotenv import load_dotenv
import os
import base64
import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

if os.path.exists(".env"):
    load_dotenv(".env", override=True)
    print("Loaded .env configuration")
else:
    load_dotenv()
    print("Loaded .env configuration")

class SupabaseManager:
    _instance = None
    _client: Optional[SupabaseClient] = None
    _lock = asyncio.Lock()
    _initialized = False

    def __init__(self):
        self._loop = None
    
    @classmethod
    async def get_client(cls) -> SupabaseClient:
        """Get or create a Supabase client instance."""
        if not cls._instance:
            cls._instance = cls()
            
        if not cls._instance._loop:
            cls._instance._loop = asyncio.get_running_loop()
        
        async with cls._lock:
            if not cls._client or cls._instance._loop != asyncio.get_running_loop():
                settings = get_settings()
                try:
                    # Validate service role key
                    payload = base64.b64decode(settings.SUPABASE_KEY.split('.')[1] + '==').decode('utf-8')
                    if '"role":"service_role"' not in payload:
                        raise ValueError("Invalid Supabase key - must be a service role key")
                    
                    # If we have an existing client in a different loop, clean it up first
                    if cls._client:
                        await cls.cleanup()
                    
                    logger.info("Initializing new Supabase client")
                    cls._client = await create_client(
                        settings.SUPABASE_URL,
                        settings.SUPABASE_KEY
                    )
                    cls._initialized = True
                except Exception as e:
                    logger.error(f"Failed to initialize Supabase client: {str(e)}")
                    cls._initialized = False
                    raise
        
        return cls._client

    @classmethod
    async def cleanup(cls):
        """Cleanup the Supabase client."""
        async with cls._lock:
            if cls._client:
                try:
                    if cls._initialized:
                        await cls._client.auth.sign_out()
                except Exception as e:
                    logger.error(f"Error during Supabase cleanup: {str(e)}")
                finally:
                    cls._client = None
                    cls._instance = None
                    cls._initialized = False

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the client is properly initialized."""
        return cls._initialized

async def get_supabase() -> SupabaseClient:
    """Get the Supabase client instance."""
    return await SupabaseManager.get_client()

async def cleanup_supabase():
    """Cleanup Supabase client."""
    await SupabaseManager.cleanup()

class Settings(BaseSettings):
    """Application settings."""
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Mortgage Deed Management API"
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Email Configuration
    MAILGUN_API_KEY: str
    MAILGUN_DOMAIN: str
    EMAILS_FROM_EMAIL: str
    EMAILS_FROM_NAME: str
    
    # Frontend Configuration
    FRONTEND_URL: str
    
    # Backend Configuration
    BACKEND_URL: str

    # CORS Configuration
    BACKEND_CORS_ORIGINS: str
    
    # Environment
    ENVIRONMENT: str = "development"
    
    @validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Convert CORS origins to the correct format."""
        if isinstance(v, str):
            if v == "*":
                return v
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 