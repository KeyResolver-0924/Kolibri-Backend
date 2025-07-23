from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging
from api.schemas.mortgage_deed import AuditLogResponse
from api.config import get_supabase
from supabase._async.client import AsyncClient as SupabaseClient
from api.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["audit-logs"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/mortgage-deeds/{deed_id}/audit-logs",
    response_model=List[AuditLogResponse],
    summary="Get deed audit logs",
    description="""
    Retrieves the complete audit log for a specific mortgage deed.
    
    The audit log contains all actions performed on the deed, including:
    - Status changes
    - Signature events
    - Notification events
    
    Results are ordered by timestamp (most recent first).
    """,
    responses={
        200: {
            "description": "Audit log entries",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "deed_id": 1,
                            "action_type": "SIGNING_INITIATED",
                            "user_id": "user-123",
                            "timestamp": "2024-01-20T12:00:00",
                            "description": "Signing process initiated for deed"
                        },
                        {
                            "id": 2,
                            "deed_id": 1,
                            "action_type": "BORROWER_SIGNED",
                            "user_id": "user-456",
                            "timestamp": "2024-01-20T12:30:00",
                            "description": "Borrower completed signing the deed"
                        }
                    ]
                }
            }
        },
        404: {"description": "Mortgage deed not found"}
    }
)
async def get_deed_audit_logs(
    deed_id: int,
    current_user: dict = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase)
) -> List[AuditLogResponse]:
    """Get the audit log for a specific deed"""
    try:
        # First verify the deed exists
        deed_result = await supabase.table("mortgage_deeds").select(
            "id"
        ).eq("id", deed_id).single().execute()
        
        if not deed_result.data:
            raise HTTPException(status_code=404, detail="Mortgage deed not found")
    
        # Get audit logs
        result = await supabase.table("audit_logs").select(
            "*"
        ).eq("deed_id", deed_id).order("timestamp", desc=True).execute()
        
        if not result.data:
            return []
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_deed_audit_logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 