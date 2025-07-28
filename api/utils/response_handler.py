from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional, Union
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ApiResponse:
    """Standardized API response wrapper."""
    
    def __init__(
        self,
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        cache_control: Optional[str] = None
    ):
        self.data = data
        self.message = message
        self.status_code = status_code
        self.headers = headers or {}
        self.cache_control = cache_control
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        return {
            "success": self.status_code < 400,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
            "status_code": self.status_code
        }
    
    def to_response(self) -> JSONResponse:
        """Convert to FastAPI JSONResponse."""
        response_headers = {
            "Content-Type": "application/json",
            "X-Response-Time": str(datetime.utcnow().timestamp()),
            **self.headers
        }
        
        if self.cache_control:
            response_headers["Cache-Control"] = self.cache_control
        
        return JSONResponse(
            content=self.to_dict(),
            status_code=self.status_code,
            headers=response_headers
        )

def create_success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    headers: Optional[Dict[str, str]] = None,
    cache_control: str = "public, max-age=300"  # 5 minutes default cache
) -> JSONResponse:
    """Create a standardized success response."""
    response = ApiResponse(
        data=data,
        message=message,
        status_code=status_code,
        headers=headers,
        cache_control=cache_control
    )
    
    logger.info(f"Success response: {message}", extra={
        "status_code": status_code,
        "data_type": type(data).__name__ if data else None
    })
    
    return response.to_response()

def create_error_response(
    message: str,
    status_code: int = 400,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create a standardized error response."""
    error_data = {
        "error_code": error_code,
        "details": details
    }
    
    response = ApiResponse(
        data=error_data,
        message=message,
        status_code=status_code
    )
    
    logger.error(f"Error response: {message}", extra={
        "status_code": status_code,
        "error_code": error_code,
        "details": details
    })
    
    return response.to_response()

def create_paginated_response(
    data: list,
    total_count: int,
    current_page: int,
    page_size: int,
    message: str = "Data retrieved successfully"
) -> JSONResponse:
    """Create a standardized paginated response."""
    total_pages = (total_count + page_size - 1) // page_size
    
    pagination_data = {
        "items": data,
        "pagination": {
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": current_page,
            "page_size": page_size,
            "has_next": current_page < total_pages,
            "has_previous": current_page > 1
        }
    }
    
    headers = {
        "X-Total-Count": str(total_count),
        "X-Total-Pages": str(total_pages),
        "X-Current-Page": str(current_page),
        "X-Page-Size": str(page_size)
    }
    
    return create_success_response(
        data=pagination_data,
        message=message,
        headers=headers,
        cache_control="public, max-age=60"  # 1 minute cache for paginated data
    )

def handle_database_error(error: Exception, operation: str) -> HTTPException:
    """Handle database errors and return appropriate HTTP exceptions."""
    error_message = str(error)
    
    # Log the error with context
    logger.error(f"Database error during {operation}: {error_message}", extra={
        "operation": operation,
        "error_type": type(error).__name__,
        "error_message": error_message
    })
    
    # Map common database errors to HTTP status codes
    if "duplicate key" in error_message.lower() or "already exists" in error_message.lower():
        return HTTPException(
            status_code=409,
            detail=f"Resource already exists: {error_message}"
        )
    elif "not found" in error_message.lower() or "does not exist" in error_message.lower():
        return HTTPException(
            status_code=404,
            detail=f"Resource not found: {error_message}"
        )
    elif "permission" in error_message.lower() or "access denied" in error_message.lower():
        return HTTPException(
            status_code=403,
            detail=f"Access denied: {error_message}"
        )
    elif "validation" in error_message.lower() or "invalid" in error_message.lower():
        return HTTPException(
            status_code=422,
            detail=f"Validation error: {error_message}"
        )
    else:
        return HTTPException(
            status_code=500,
            detail=f"Internal server error during {operation}"
        )

def validate_and_sanitize_data(data: Any, required_fields: list = None) -> Dict[str, Any]:
    """Validate and sanitize input data."""
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    
    # Remove None values and empty strings
    sanitized = {}
    for key, value in data.items():
        if value is not None and value != "":
            sanitized[key] = value
    
    # Check required fields
    if required_fields:
        missing_fields = [field for field in required_fields if field not in sanitized]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    return sanitized

def add_response_headers(response: Response, headers: Dict[str, str]) -> None:
    """Add custom headers to response."""
    for key, value in headers.items():
        response.headers[key] = value

def create_audit_response(
    action: str,
    resource_id: Union[int, str],
    user_id: str,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized audit response."""
    return {
        "audit": {
            "action": action,
            "resource_id": resource_id,
            "user_id": user_id,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
    }

# Response middleware for consistent logging
async def log_response_middleware(request, call_next):
    """Middleware to log request/response details."""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}", extra={
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client_ip": request.client.host if request.client else None
    })
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    response_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Log response
    logger.info(f"Response: {response.status_code} ({response_time:.3f}s)", extra={
        "status_code": response.status_code,
        "response_time": response_time,
        "content_length": len(response.body) if hasattr(response, 'body') else 0
    })
    
    # Add response time header
    response.headers["X-Response-Time"] = f"{response_time:.3f}s"
    
    return response 