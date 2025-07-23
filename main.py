from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import sys

from api.config import get_settings, SupabaseManager
from api.routers import mortgage_deeds
# , housing_cooperative, signing, statistics, audit_logs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application...")
    settings = get_settings()
    logger.info(f"Loaded settings - Supabase URL: {settings.SUPABASE_URL}")
    logger.info(f"Supabase key type: {'service_role' if len(settings.SUPABASE_KEY) > 100 else 'anon'}")
    logger.info(f"CORS origins: {settings.BACKEND_CORS_ORIGINS}")
    await SupabaseManager.get_client()  # Initialize Supabase client
    yield
    await SupabaseManager.cleanup()
    logger.info("Shutdown complete.")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Mortgage Deed Management API",
    description="The Mortgage Deed Management API provides a comprehensive solution for managing digital mortgage deeds.",
    lifespan=lifespan
)

# Get allowed origins from settings
settings = get_settings()
origins = settings.BACKEND_CORS_ORIGINS

# Add CORS middleware using origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use your configured origins here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Error handler for unauthorized access
@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=401,
        content={"detail": "Invalid authentication credentials"},
        headers={"WWW-Authenticate": "Bearer"}
    )

# Error handler for validation errors with detailed logging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for error in exc.errors():
        location = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append({
            "location": location,
            "message": error["msg"],
            "type": error["type"]
        })
    logger.error(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": error_details
        }
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": error_details
        }
    )

# Include your routers with proper prefixes and tags
app.include_router(mortgage_deeds.router, prefix="/api/mortgage-deeds", tags=["mortgage-deeds"])
# app.include_router(housing_cooperative.router, prefix="/api/housing-cooperatives", tags=["housing-cooperatives"])
# app.include_router(signing.router, prefix="/api/mortgage-deeds", tags=["signing"])
# app.include_router(statistics.router, prefix="/api/statistics", tags=["statistics"])
# app.include_router(audit_logs.router, prefix="/api", tags=["audit-logs"])

# Run with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, proxy_headers=True)
