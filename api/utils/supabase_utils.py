from fastapi import HTTPException, status
from supabase._async.client import AsyncClient
import logging
import postgrest.exceptions
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

def convert_decimals_to_float(obj):
    """
    Recursively convert all Decimal values to float in a data structure.
    
    Args:
        obj: Any object (dict, list, Decimal, or other types)
        
    Returns:
        Object with all Decimal values converted to float
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    else:
        return obj

async def handle_supabase_operation(operation_name: str, operation, error_msg: str):
    """
    Generic handler for Supabase operations with consistent error handling and logging.
    
    Args:
        operation_name: Name of the operation for logging
        operation: Async operation to execute
        error_msg: User-facing error message if operation fails
        
    Returns:
        The result of the operation
        
    Raises:
        HTTPException: If operation fails
    """
    try:
        result = await operation
        logger.info(f"Successfully completed {operation_name}")
        return result
    except postgrest.exceptions.APIError as e:
        logger.error(f"Failed to {operation_name}: %s", str(e), exc_info=True)
        
        # Handle specific Postgrest error codes
        if e.code == "PGRST116":  # No rows returned
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif e.code == "23505":  # Unique violation
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
    except Exception as e:
        logger.error(f"Failed to {operation_name}: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        ) 