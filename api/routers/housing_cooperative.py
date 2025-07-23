from fastapi import APIRouter, HTTPException, Depends, Query, Response, status
from supabase._async.client import AsyncClient
from typing import Annotated, List, Dict, Any
import logging
from math import ceil
import postgrest.exceptions

from ..schemas.housing_cooperative import (
    HousingCooperativeResponse, 
    HousingCooperativeCreate,
    HousingCooperativeUpdate
)
from ..config import get_supabase
from ..dependencies.auth import get_current_user
from ..utils.supabase_utils import handle_supabase_operation
from ..utils.audit import create_audit_log

logger = logging.getLogger(__name__)

# Router Configuration
router = APIRouter(
    prefix="",
    tags=["housing-cooperatives"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"},
        409: {"description": "Conflict with existing resource"},
        500: {"description": "Internal server error"}
    }
)

# Helper Functions
async def get_cooperative_by_org_number(
    organization_number: str,
    supabase: AsyncClient
) -> Dict[str, Any]:
    """
    Helper function to get a cooperative by organization number.
    
    Args:
        organization_number: The organization number to look up
        supabase: Supabase client instance
        
    Returns:
        Dict containing the housing cooperative data
        
    Raises:
        HTTPException: If cooperative is not found
    """
    try:
        response = await handle_supabase_operation(
            f"fetch cooperative {organization_number}",
            supabase.table("housing_cooperatives")
                .select("*")
                .eq("organisation_number", organization_number)
                .single()
                .execute(),
            f"Failed to fetch housing cooperative {organization_number}"
        )
        
        if not response or not response.data:
            logger.info(f"Housing cooperative {organization_number} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Housing cooperative with organization number {organization_number} not found"
            )
        return response.data
    except postgrest.exceptions.APIError as e:
        if e.code == "PGRST116":  # No rows returned
            logger.info(f"Housing cooperative {organization_number} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Housing cooperative with organization number {organization_number} not found"
            )
        logger.error(f"Database error when fetching cooperative {organization_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        ) from e

# CRUD Endpoints

# Create
@router.post(
    "",
    response_model=HousingCooperativeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new housing cooperative",
    description="""
    Creates a new housing cooperative with the provided details.
    
    Returns:
    - 201: Successfully created
    - 409: Cooperative with the same organization number already exists
    """
)
async def create_housing_cooperative(
    cooperative: HousingCooperativeCreate,
    current_user: dict = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase)
) -> HousingCooperativeResponse:
    """Create a new housing cooperative."""
    # Check if cooperative already exists
    existing = await handle_supabase_operation(
        f"check existing cooperative {cooperative.organisation_number}",
        supabase.table("housing_cooperatives")
            .select("*")
            .eq("organisation_number", cooperative.organisation_number)
            .execute(),
        f"Failed to check existing cooperative {cooperative.organisation_number}"
    )
    
    if existing.data:
        logger.warning(
            f"Attempted to create duplicate cooperative {cooperative.organisation_number}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Housing cooperative with this organization number already exists"
        )
    
    # Create the cooperative
    result = await handle_supabase_operation(
        f"create cooperative {cooperative.organisation_number}",
        supabase.table("housing_cooperatives").insert({
            **cooperative.model_dump(),
            "created_by": current_user["id"]
        }).execute(),
        f"Failed to create housing cooperative {cooperative.organisation_number}"
    )
    
    if not result.data:
        logger.error(f"No data returned after creating cooperative {cooperative.organisation_number}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create housing cooperative"
        )
    
    # Create audit log for cooperative creation
    await create_audit_log(
        supabase,
        result.data[0]["id"],
        "COOPERATIVE_CREATED",
        current_user["id"],
        f"Created housing cooperative '{cooperative.name}' (org.nr: {cooperative.organisation_number})"
    )
    
    logger.info(f"Successfully created cooperative {cooperative.organisation_number}")
    return HousingCooperativeResponse(**result.data[0])

# Read
@router.get(
    "",
    response_model=List[HousingCooperativeResponse],
    summary="List housing cooperatives",
    description="""
    Retrieves a paginated list of all housing cooperatives.
    
    Pagination is controlled through query parameters:
    - page: Page number (starts at 1)
    - page_size: Number of items per page (1-100)
    
    Response headers include:
    - X-Total-Count: Total number of cooperatives
    - X-Total-Pages: Total number of pages
    - X-Current-Page: Current page number
    - X-Page-Size: Number of items per page
    """
)
async def list_housing_cooperatives(
    response: Response,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page (max 100)"),
    supabase: AsyncClient = Depends(get_supabase),
    current_user: dict = Depends(get_current_user)
) -> List[HousingCooperativeResponse]:
    """List all housing cooperatives with pagination."""
    try:
        offset = (page - 1) * page_size
        
        # Get total count
        count_response = await handle_supabase_operation(
            "count housing cooperatives",
            supabase.table("housing_cooperatives").select("*", count="exact").execute(),
            "Failed to count housing cooperatives"
        )
        total_count = count_response.count if count_response.count is not None else 0
        logger.info(f"Total housing cooperatives count: {total_count}")
        
        # Fetch paginated data
        data_response = await handle_supabase_operation(
            f"list housing cooperatives page {page}",
            supabase.table("housing_cooperatives")
                .select("*")
                .order("id", desc=True)  # Sort by id descending to show newest first
                .range(offset, offset + page_size - 1)
                .execute(),
            "Failed to list housing cooperatives"
        )
            
        if not data_response.data:
            logger.warning("No housing cooperatives found in the response")
            return []
            
        logger.info(f"Found {len(data_response.data)} housing cooperatives in page {page}")
        logger.debug(f"Housing cooperatives data: {data_response.data}")
            
        # Set pagination headers
        total_pages = ceil(total_count / page_size)
        response.headers.update({
            "X-Total-Count": str(total_count),
            "X-Total-Pages": str(total_pages),
            "X-Current-Page": str(page),
            "X-Page-Size": str(page_size)
        })
            
        return [HousingCooperativeResponse(**data) for data in data_response.data]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list cooperatives: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list housing cooperatives"
        )

@router.get(
    "/{organization_number}",
    response_model=HousingCooperativeResponse,
    summary="Get housing cooperative details",
    description="""
    Retrieves detailed information about a specific housing cooperative by its organization number.
    
    Returns a 404 error if the cooperative is not found.
    """
)
async def get_housing_cooperative_details(
    organization_number: str,
    current_user: dict = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase)
) -> HousingCooperativeResponse:
    """Fetch housing cooperative details by organization number."""
    data = await get_cooperative_by_org_number(organization_number, supabase)
    return HousingCooperativeResponse(**data)

# Update
@router.put(
    "/{organization_number}",
    response_model=HousingCooperativeResponse,
    summary="Update housing cooperative details",
    description="""
    Updates the details of an existing housing cooperative.
    
    Returns:
    - 200: Successfully updated
    - 404: Cooperative not found
    """
)
async def update_housing_cooperative(
    organization_number: str,
    cooperative: HousingCooperativeUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase)
) -> HousingCooperativeResponse:
    """Update housing cooperative details."""
    # Log the raw update data for debugging
    update_data = cooperative.model_dump(exclude_unset=True)
    logger.info(
        "Updating housing cooperative",
        extra={
            "organization_number": organization_number,
            "update_data": update_data,
            "fields_to_update": list(update_data.keys())
        }
    )
    
    # Verify cooperative exists
    existing = await get_cooperative_by_org_number(organization_number, supabase)
    
    # Include all fields that were explicitly set, even if they are None
    # This allows clearing optional fields by setting them to empty string or null
    filtered_update_data = update_data
    
    logger.info(
        "Filtered update data",
        extra={
            "filtered_fields": filtered_update_data
        }
    )
    
    if not filtered_update_data:
        logger.warning("No fields to update")
        return HousingCooperativeResponse(**existing)
    
    # Update cooperative
    result = await handle_supabase_operation(
        f"update cooperative {organization_number}",
        supabase.table("housing_cooperatives")
            .update(filtered_update_data)
            .eq("organisation_number", organization_number)
            .execute(),
        f"Failed to update housing cooperative {organization_number}"
    )
    
    if not result.data:
        logger.error(f"No data returned after updating cooperative {organization_number}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update housing cooperative"
        )
    
    # Create audit log for cooperative update
    await create_audit_log(
        supabase,
        existing["id"],
        "COOPERATIVE_UPDATED",
        current_user["id"],
        f"Updated housing cooperative '{existing['name']}' (org.nr: {organization_number})"
    )
    
    logger.info(
        f"Successfully updated cooperative {organization_number}",
        extra={
            "updated_fields": list(filtered_update_data.keys())
        }
    )
    return HousingCooperativeResponse(**result.data[0])

# Delete
@router.delete(
    "/{organization_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete housing cooperative",
    description="""
    Deletes a housing cooperative if it has no active mortgage deeds.
    
    Returns:
    - 204: Successfully deleted
    - 404: Cooperative not found
    - 409: Cannot delete due to active mortgage deeds
    """
)
async def delete_housing_cooperative(
    organization_number: str,
    current_user: dict = Depends(get_current_user),
    supabase: AsyncClient = Depends(get_supabase)
):
    """Delete housing cooperative if it has no deeds."""
    # Get existing cooperative
    existing = await get_cooperative_by_org_number(organization_number, supabase)
    
    # Check for any deeds (both active and completed)
    deeds = await handle_supabase_operation(
        f"check deeds for cooperative {organization_number}",
        supabase.table("mortgage_deeds")
            .select("id")
            .eq("housing_cooperative_id", existing["id"])
            .execute(),
        f"Failed to check deeds for cooperative {organization_number}"
    )
    
    if deeds.data:
        logger.warning(
            f"Attempted to delete cooperative {organization_number} with existing deeds",
            extra={"deeds_count": len(deeds.data)}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete housing cooperative with existing mortgage deeds"
        )
    
    try:
        # Create audit log before deletion
        await create_audit_log(
            supabase,
            existing["id"],
            "COOPERATIVE_DELETED",
            current_user["id"],
            f"Deleted housing cooperative '{existing['name']}' (org.nr: {organization_number})"
        )

        # Delete cooperative
        delete_result = await handle_supabase_operation(
            f"delete cooperative {organization_number}",
            supabase.table("housing_cooperatives")
                .delete()
                .eq("organisation_number", organization_number)
                .execute(),
            f"Failed to delete housing cooperative {organization_number}"
        )
        
        logger.info(f"Successfully deleted cooperative {organization_number}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except postgrest.exceptions.APIError as e:
        if e.code == "23503":  # Foreign key constraint violation
            logger.warning(
                f"Foreign key constraint violation when deleting cooperative {organization_number}",
                extra={"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete housing cooperative with existing mortgage deeds"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete housing cooperative"
        ) 