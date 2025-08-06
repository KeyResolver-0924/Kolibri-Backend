from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from api.config import get_supabase
from supabase._async.client import AsyncClient as SupabaseClient
from api.schemas.statistics import StatsSummary, StatusDurationStats, TimelineStats
from api.dependencies.auth import get_current_user
from api.utils.supabase_utils import handle_supabase_operation

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["statistics"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/summary",
    response_model=StatsSummary,
    summary="Get statistics summary",
    description="""
    Retrieves a summary of key statistics about the mortgage deed system.
    
    Includes:
    - Total number of mortgage deeds
    - Total number of housing cooperatives
    - Distribution of deeds across different statuses
    - Average number of borrowers per deed
    """
)
async def get_stats_summary(
    current_user: dict = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase)
) -> StatsSummary:
    """Get overall statistics summary for mortgage deeds"""
    try:
        logger.info("Fetching statistics summary")
        
        # Get total count of deeds
        total_count = await supabase.table('mortgage_deeds').select('*', count='exact').execute()
        
        # Get total count of cooperatives
        total_cooperatives = await supabase.table('housing_cooperatives').select('*', count='exact').execute()
        
        # Get all deeds with their status
        status_data = await supabase.table('mortgage_deeds').select('status').execute()
        
        # Get all borrowers with their deed_ids
        borrowers_data = await supabase.table('borrowers').select('deed_id').execute()
        
        # Calculate status distribution
        status_distribution = {}
        for item in status_data.data:
            status = item['status']
            status_distribution[status] = status_distribution.get(status, 0) + 1
        
        # Calculate average borrowers per deed
        deed_borrower_counts = {}
        for item in borrowers_data.data:
            deed_id = item['deed_id']
            deed_borrower_counts[deed_id] = deed_borrower_counts.get(deed_id, 0) + 1
        
        total_deeds = total_count.count if total_count.count else 0
        total_borrowers = len(borrowers_data.data) if borrowers_data.data else 0
        avg_borrowers = round(total_borrowers / total_deeds, 2) if total_deeds > 0 else 0
        
        logger.info("Statistics summary calculated: %d deeds, %d cooperatives", 
                   total_deeds, 
                   total_cooperatives.count if total_cooperatives.count else 0)
        logger.debug("Status distribution: %s", status_distribution)
        
        return StatsSummary(
            total_deeds=total_deeds,
            total_cooperatives=total_cooperatives.count if total_cooperatives.count else 0,
            status_distribution=status_distribution,
            average_borrowers_per_deed=avg_borrowers
        )
    except Exception as e:
        logger.error("Failed to fetch statistics summary: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/status-duration",
    response_model=List[StatusDurationStats],
    summary="Get status duration statistics",
    description="""
    Calculates the average, minimum, and maximum time deeds spend in each status.
    
    This endpoint analyzes the audit logs to determine:
    - Average duration in each status
    - Minimum time spent in each status
    - Maximum time spent in each status
    
    All durations are reported in hours.
    """
)
async def get_status_duration_stats(
    current_user: dict = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase)
) -> List[StatusDurationStats]:
    """Get average duration spent in each status"""
    try:
        logger.info("Calculating status duration statistics")
        
        # Get audit log entries for status changes
        audit_logs = await supabase.table('audit_logs')\
            .select('deed_id, action_type, timestamp')\
            .like('action_type', 'STATUS_CHANGE%')\
            .order('deed_id, timestamp')\
            .execute()
        
        if not audit_logs.data:
            logger.info("No status change data found in audit logs")
            return []
        
        # Process audit logs to calculate durations
        status_durations: Dict[str, List[float]] = {}
        current_deed = None
        last_timestamp = None
        last_status = None
        
        for log in audit_logs.data:
            if current_deed != log['deed_id']:
                current_deed = log['deed_id']
                last_timestamp = None
                last_status = None
                
            if last_timestamp and last_status:
                duration = (datetime.fromisoformat(log['timestamp']) - 
                          datetime.fromisoformat(last_timestamp)).total_seconds() / 3600  # Convert to hours
                
                if last_status not in status_durations:
                    status_durations[last_status] = []
                status_durations[last_status].append(duration)
            
            last_timestamp = log['timestamp']
            last_status = log['action_type'].replace('STATUS_CHANGE_TO_', '')
        
        # Calculate averages
        stats = [
            StatusDurationStats(
                status=status,
                average_duration_hours=round(sum(durations) / len(durations), 2),
                min_duration_hours=round(min(durations), 2),
                max_duration_hours=round(max(durations), 2)
            )
            for status, durations in status_durations.items()
        ]
        
        logger.info("Calculated duration statistics for %d different statuses", len(stats))
        logger.debug("Status duration details: %s", stats)
        
        return stats
    except Exception as e:
        logger.error("Failed to calculate status duration statistics: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/timeline",
    response_model=List[TimelineStats],
    summary="Get timeline statistics",
    description="""
    Retrieves daily statistics for deed creation and completion.
    
    For each day in the specified time range, returns:
    - Number of new deeds created
    - Number of deeds completed
    
    The timeline defaults to the last 30 days but can be customized using the days parameter.
    Results are sorted chronologically.
    """
)
async def get_timeline_stats(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase)
) -> List[TimelineStats]:
    """Get daily statistics for the specified number of days"""
    try:
        logger.info("Fetching timeline statistics for last %d days", days)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get daily counts of new deeds using raw SQL
        new_deeds = await supabase.rpc(
            'get_daily_new_deeds',
            {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        ).execute()
        
        # Get daily counts of completed deeds using raw SQL
        completed_deeds = await supabase.rpc(
            'get_daily_completed_deeds',
            {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        ).execute()
        
        # Create a map of dates to stats
        timeline_map: Dict[str, Dict] = {}
        
        # Process new deeds
        if new_deeds.data:
            for item in new_deeds.data:
                date = item['date']
                if date not in timeline_map:
                    timeline_map[date] = {'date': date, 'new_deeds': 0, 'completed_deeds': 0}
                timeline_map[date]['new_deeds'] = item['count']
        
        # Process completed deeds
        if completed_deeds.data:
            for item in completed_deeds.data:
                date = item['date']
                if date not in timeline_map:
                    timeline_map[date] = {'date': date, 'new_deeds': 0, 'completed_deeds': 0}
                timeline_map[date]['completed_deeds'] = item['count']
        
        # Convert to list and sort by date
        timeline = [TimelineStats(**stats) for stats in timeline_map.values()]
        sorted_timeline = sorted(timeline, key=lambda x: x.date)
        
        logger.info("Generated timeline statistics for %d days", len(sorted_timeline))
        logger.debug("Timeline details: %s", sorted_timeline)
        
        return sorted_timeline
    
    except Exception as e:
        logger.error("Failed to generate timeline statistics: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get(
    "/bank-dashboard",
    summary="Get bank dashboard statistics",
    description="Get dashboard statistics for bank users including total deeds, pending signatures, and completed deeds."
)
async def get_bank_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase)
):
    """
    Get dashboard statistics for bank users.
    
    Args:
        current_user: Current authenticated user
        supabase: Supabase client instance
        
    Returns:
        Dashboard statistics for bank users
        
    Raises:
        HTTPException: If user is not a bank user or if query fails
    """
    logger.info(f"Bank dashboard request - User role: {current_user.get('role')}, User ID: {current_user.get('id')}")
    
    if current_user.get("role") != "bank_user":
        logger.error(f"Access denied - User role: {current_user.get('role')}")
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only bank users can access this endpoint."
        )
    
    try:
        # Get bank_id from user metadata
        bank_id = current_user.get("bank_id")
        if not bank_id:
            logger.error("No bank_id found in user metadata")
            raise HTTPException(
                status_code=400,
                detail="Bank ID not found in user profile"
            )
        
        logger.info(f"Querying deeds for bank_id: {bank_id}")
        
        # Get total deeds for this bank
        total_deeds_result = await handle_supabase_operation(
            operation_name="get total deeds for bank",
            operation=supabase.table("mortgage_deeds")
                .select("id", count="exact")
                .eq("bank_id", int(bank_id))
                .execute(),
            error_msg="Failed to get total deeds count"
        )
        
        # Get pending signatures (deeds in progress)
        pending_signatures_result = await handle_supabase_operation(
            operation_name="get pending signatures for bank",
            operation=supabase.table("mortgage_deeds")
                .select("id", count="exact")
                .eq("bank_id", int(bank_id))
                .in_("status", ["PENDING_BORROWER_SIGNATURE", "PENDING_HOUSING_COOPERATIVE_SIGNATURE", "CREATED"])
                .execute(),
            error_msg="Failed to get pending signatures count"
        )
        
        # Get completed deeds
        completed_deeds_result = await handle_supabase_operation(
            operation_name="get completed deeds for bank",
            operation=supabase.table("mortgage_deeds")
                .select("id", count="exact")
                .eq("bank_id", int(bank_id))
                .eq("status", "COMPLETED")
                .execute(),
            error_msg="Failed to get completed deeds count"
        )
        
        return {
            "total_deeds": total_deeds_result.count or 0,
            "pending_signatures": pending_signatures_result.count or 0,
            "completed_deeds": completed_deeds_result.count or 0,
            "bank_name": current_user.get("bank_name", "Unknown Bank")
        }
        
    except Exception as e:
        logger.error(f"Error getting bank dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get dashboard statistics"
        )

@router.get(
    "/cooperative-dashboard",
    summary="Get cooperative dashboard statistics",
    description="Get dashboard statistics for cooperative admins including pending reviews, approved deeds, and total units."
)
async def get_cooperative_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase)
):
    """
    Get dashboard statistics for cooperative admins.
    
    Args:
        current_user: Current authenticated user
        supabase: Supabase client instance
        
    Returns:
        Dashboard statistics for cooperative admins
        
    Raises:
        HTTPException: If user is not a cooperative admin or if query fails
    """
    if current_user.get("role") != "cooperative_admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only cooperative admins can access this endpoint."
        )
    
    try:
        # Get cooperative ID for this admin
        cooperative_result = await handle_supabase_operation(
            operation_name="get cooperative for admin",
            operation=supabase.table("housing_cooperatives")
                .select("id, name")
                .eq("created_by", current_user["id"])
                .single()
                .execute(),
            error_msg="Failed to get cooperative details"
        )
        
        cooperative_id = cooperative_result.data["id"]
        # For now, set total_units to 0 since it's not in the schema
        total_units = 0
        
        # Get pending reviews (deeds awaiting cooperative approval)
        pending_reviews_result = await handle_supabase_operation(
            operation_name="get pending reviews for cooperative",
            operation=supabase.table("mortgage_deeds")
                .select("id", count="exact")
                .eq("housing_cooperative_id", cooperative_id)
                .eq("status", "PENDING_HOUSING_COOPERATIVE_SIGNATURE")
                .execute(),
            error_msg="Failed to get pending reviews count"
        )
        
        # Get approved deeds this month
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        approved_this_month_result = await handle_supabase_operation(
            operation_name="get approved deeds this month",
            operation=supabase.table("mortgage_deeds")
                .select("id", count="exact")
                .eq("housing_cooperative_id", cooperative_id)
                .eq("status", "COMPLETED")
                .gte("created_at", this_month_start.isoformat())
                .execute(),
            error_msg="Failed to get approved deeds count"
        )
        
        # Get active deeds (currently processing)
        active_deeds_result = await handle_supabase_operation(
            operation_name="get active deeds for cooperative",
            operation=supabase.table("mortgage_deeds")
                .select("id", count="exact")
                .eq("housing_cooperative_id", cooperative_id)
                .in_("status", ["CREATED", "PENDING_BORROWER_SIGNATURE", "PENDING_HOUSING_COOPERATIVE_SIGNATURE"])
                .execute(),
            error_msg="Failed to get active deeds count"
        )
        
        return {
            "pending_reviews": pending_reviews_result.count or 0,
            "approved_this_month": approved_this_month_result.count or 0,
            "total_units": total_units,
            "active_deeds": active_deeds_result.count or 0,
            "cooperative_name": cooperative_result.data.get("name", "Unknown Cooperative")
        }
        
    except Exception as e:
        logger.error(f"Error getting cooperative dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get dashboard statistics"
        )

@router.get(
    "/accounting-dashboard",
    summary="Get accounting firm dashboard statistics",
    description="Get dashboard statistics for accounting firms including active cooperatives, pending actions, and processing metrics."
)
async def get_accounting_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase)
):
    """
    Get dashboard statistics for accounting firms.
    
    Args:
        current_user: Current authenticated user
        supabase: Supabase client instance
        
    Returns:
        Dashboard statistics for accounting firms
        
    Raises:
        HTTPException: If user is not an accounting firm or if query fails
    """
    logger.info(f"Accounting dashboard request - User role: {current_user.get('role')}, User ID: {current_user.get('id')}")
    
    if current_user.get("role") != "accounting_firm":
        logger.error(f"Access denied - User role: {current_user.get('role')}")
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only accounting firms can access this endpoint."
        )
    
    try:
        logger.info("Getting total cooperatives count...")
        # Get total cooperatives in the system
        total_cooperatives_result = await handle_supabase_operation(
            operation_name="get total cooperatives",
            operation=supabase.table("housing_cooperatives")
                .select("id", count="exact")
                .execute(),
            error_msg="Failed to get total cooperatives count"
        )
        logger.info(f"Total cooperatives: {total_cooperatives_result.count}")
        
        logger.info("Getting pending actions count...")
        # Get pending actions (deeds requiring attention)
        pending_actions_result = await handle_supabase_operation(
            operation_name="get pending actions",
            operation=supabase.table("mortgage_deeds")
                .select("id", count="exact")
                .in_("status", ["CREATED", "PENDING_BORROWER_SIGNATURE"])
                .execute(),
            error_msg="Failed to get pending actions count"
        )
        logger.info(f"Pending actions: {pending_actions_result.count}")
        
        logger.info("Getting processed deeds this month...")
        # Get processed deeds this month
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        processed_this_month_result = await handle_supabase_operation(
            operation_name="get processed deeds this month",
            operation=supabase.table("mortgage_deeds")
                .select("id", count="exact")
                .gte("created_at", this_month_start.isoformat())
                .execute(),
            error_msg="Failed to get processed deeds count"
        )
        logger.info(f"Processed this month: {processed_this_month_result.count}")
        
        # Calculate average processing time (mock data for now)
        avg_processing = "1.3 days"  # This would be calculated from actual data
        
        return {
            "active_cooperatives": total_cooperatives_result.count or 0,
            "pending_actions": pending_actions_result.count or 0,
            "processed_this_month": processed_this_month_result.count or 0,
            "avg_processing": avg_processing,
            "accounting_firm_name": current_user.get("user_name", "Unknown Firm")
        }
        
    except Exception as e:
        logger.error(f"Error getting accounting dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get dashboard statistics"
        ) 