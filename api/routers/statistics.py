from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
from datetime import datetime, timedelta
import logging
from api.config import get_supabase
from supabase._async.client import AsyncClient as SupabaseClient
from api.schemas.statistics import StatsSummary, StatusDurationStats, TimelineStats
from api.dependencies.auth import get_current_user

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