from supabase._async.client import AsyncClient as SupabaseClient
from api.utils.supabase_utils import handle_supabase_operation
from typing import Optional

async def create_audit_log(
    supabase: SupabaseClient,
    entity_id: int,
    action_type: str,
    user_id: str,
    description: str,
    deed_id: Optional[int] = None
) -> None:
    """
    Create an audit log entry for system actions.
    
    Args:
        supabase: Supabase client instance
        entity_id: ID of the entity being acted upon (e.g., deed_id, cooperative_id)
        action_type: Type of action performed (e.g., DEED_CREATED, COOPERATIVE_UPDATED)
        user_id: ID of the user performing the action
        description: Human readable description of the action
        deed_id: Optional ID of related mortgage deed (if action is deed-related)
    """
    log_entry = {
        "action_type": action_type,
        "user_id": user_id,
        "entity_id": entity_id,
        "description": description
    }
    
    if deed_id is not None:
        log_entry["deed_id"] = deed_id
    
    await handle_supabase_operation(
        operation_name=f"create audit log for {action_type}",
        operation=supabase.table("audit_logs").insert(log_entry).execute(),
        error_msg="Failed to create audit log"
    ) 