# Standard library imports
from datetime import datetime
import logging
from typing import List, Optional

# FastAPI imports
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi import Response

# Local imports
from api.config import get_supabase, get_settings
from api.dependencies.auth import get_current_user
from api.schemas.mortgage_deed import (
    MortgageDeedCreate,
    MortgageDeedUpdate)
from api.utils.audit import create_audit_log
from api.utils.supabase_utils import handle_supabase_operation
from api.utils.email_utils import send_email
from supabase._async.client import AsyncClient as SupabaseClient

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["mortgage-deeds"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Mortgage deed not found"},
        409: {"description": "Conflict with existing resource"},
        500: {"description": "Internal server error"}
    }
)

async def send_mortgage_deed_notifications(
    deed_id: int,
    supabase: SupabaseClient,
    settings
) -> bool:
    """
    Send notifications to borrowers and housing cooperatives after mortgage deed creation.
    
    Args:
        deed_id: ID of the created mortgage deed
        supabase: Supabase client instance
        settings: Application settings
        
    Returns:
        bool: True if all notifications were sent successfully
    """
    try:
        # Fetch the created deed with all related data
        deed_result = await handle_supabase_operation(
            operation_name=f"fetch created deed {deed_id}",
            operation=supabase.table("mortgage_data").select(
                "*, borrowers(*), housing_cooperatives(*)"
            ).eq("id", deed_id).single().execute(),
            error_msg="Failed to fetch created deed details"
        )
        
        deed = deed_result.data
        all_emails_sent = True
        
        # Send notifications to borrowers
        for borrower in deed.get("borrowers", []):
            context = {
                "borrower_name": borrower.get('name', ''),
                "deed": {
                    "reference_number": deed.get("credit_number", ""),
                    "apartment_number": deed.get("apartment_number", ""),
                    "apartment_address": deed.get("apartment_address", ""),
                    "cooperative_name": deed.get("housing_cooperative_name", ""),
                    "amount": deed.get("amount", 0),
                    "created_date": deed.get("created_at", "")
                },
                "from_name": settings.EMAILS_FROM_NAME
            }
            
            success = await send_email(
                recipient_email=borrower.get("email", ""),
                subject="Nytt pantbrev skapat - Action Required",
                template_name="borrower_notification.html",
                template_context=context,
                settings=settings
            )
            
            if not success:
                all_emails_sent = False
                logger.error(f"Failed to send email to borrower {borrower.get('email', '')}")
        
        # Send notification to housing cooperative administrator
        if deed.get("housing_cooperative_id"):
            coop_context = {
                "admin_name": deed.get("administrator_name", ""),
                "deed": {
                    "reference_number": deed.get("credit_number", ""),
                    "apartment_number": deed.get("apartment_number", ""),
                    "apartment_address": deed.get("apartment_address", ""),
                    "cooperative_name": deed.get("housing_cooperative_name", ""),
                    "borrowers": deed.get("borrowers", []),
                    "created_date": deed.get("created_at", "")
                },
                "from_name": settings.EMAILS_FROM_NAME
            }
            
            success = await send_email(
                recipient_email=deed.get("administrator_email", ""),
                subject="Nytt pantbrev skapat - Bostadsrättsförening",
                template_name="cooperative_notification.html",
                template_context=coop_context,
                settings=settings
            )
            
            if not success:
                all_emails_sent = False
                logger.error(f"Failed to send email to cooperative administrator {deed.get('administrator_email', '')}")
        
        return all_emails_sent
        
    except Exception as e:
        logger.error(f"Error sending mortgage deed notifications: {str(e)}")
        return False

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new mortgage deed",
    description="""
    Creates a new mortgage deed with the provided details and sends notifications to all parties.
    """,
    responses={
        201: {
            "description": "Mortgage deed created successfully",
        }
    }
)
async def create_mortgage_deed(
    deed: MortgageDeedCreate,
    current_user: dict = Depends(get_current_user),
    supabase: SupabaseClient = Depends(get_supabase),
    settings = Depends(get_settings)
):
    """
    Create a new mortgage deed with associated borrowers and send notifications.
    
    Args:
        deed: Mortgage deed creation data
        current_user: Current authenticated user
        supabase: Supabase client instance
        settings: Application settings
        
    Returns:
        Created mortgage deed with all relations
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        logger.info(f"Creating mortgage deed for user: {current_user.get('id')}")
        logger.info(f"Deed data: {deed.model_dump()}")
        deed_data = deed.model_dump()
        
        # Transform the data
        try:
            transformed_data = transform_deed_data(deed)
            logger.info(f"Transformed data: {transformed_data}")
        except Exception as e:
            logger.error(f"Error transforming deed data: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to transform deed data: {str(e)}"
            )

        # Create the mortgage deed
        try:
            deed_result = await handle_supabase_operation(
                operation_name="create mortgage deed",
                operation=supabase.table("mortgage_data").insert({
                    **transformed_data,
                    "created_by": current_user["id"],
                }).execute(),
                error_msg="Failed to create mortgage deed"
            )
            logger.info(f"Mortgage deed created successfully: {deed_result.data}")
        except Exception as e:
            logger.error(f"Error creating mortgage deed in database: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create mortgage deed in database: {str(e)}"
            )
        
        # Get the created deed ID
        if not deed_result.data or len(deed_result.data) == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to get created deed ID"
            )
        
        created_deed_id = deed_result.data[0]["id"]
        logger.info(f"Created deed ID: {created_deed_id}")
        
        # Send notifications to all parties
        try:
            notifications_sent = await send_mortgage_deed_notifications(
                created_deed_id,
                supabase,
                settings
            )
            logger.info(f"Notifications sent: {notifications_sent}")
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
            notifications_sent = False
        
        # Create audit log for deed creation
        try:
            await create_audit_log(
                supabase,
                created_deed_id,
                "DEED_CREATED",
                current_user["id"],
                f"Created mortgage deed {created_deed_id} for apartment {transformed_data.get('apartment_info', {}).get('apartment_number', '')} at {transformed_data.get('apartment_info', {}).get('apartment_address', '')}"
            )
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
        
        # Create audit log for notifications
        try:
            if notifications_sent:
                await create_audit_log(
                    supabase,
                    created_deed_id,
                    "NOTIFICATIONS_SENT",
                    current_user["id"],
                    f"Successfully sent notifications for mortgage deed {created_deed_id}"
                )
            else:
                await create_audit_log(
                    supabase,
                    created_deed_id,
                    "NOTIFICATION_FAILURE",
                    current_user["id"],
                    f"Failed to send some notifications for mortgage deed {created_deed_id}"
                )
        except Exception as e:
            logger.error(f"Error creating notification audit log: {str(e)}")
        
        return {
            "status": "success",
            "message": "Mortgage deed created successfully.",
            "deed_id": created_deed_id,
            "notifications_sent": notifications_sent
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_mortgage_deed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

def transform_deed_data(input_data: MortgageDeedCreate):
    """
    Transform MortgageDeedCreate model to database format.
    
    Args:
        input_data: MortgageDeedCreate model instance
        
    Returns:
        dict: Transformed data for database insertion
    """
    try:
        # Convert model to dict
        deed_dict = input_data.model_dump()
        
        # Handle credit numbers
        credit_numbers = (
            [int(deed_dict["credit_number"])]
            if not deed_dict.get("credit_numbers")
            else [int(n) for n in deed_dict["credit_numbers"]]
        )

        # Build housing cooperative info
        housing_cooperative_info = {
            "organization_number": deed_dict["organization_number"],
            "housing_cooperative_id": deed_dict["housing_cooperative_id"],
            "housing_cooperative_name": deed_dict["cooperative_name"],
            "housing_cooperative_address": deed_dict["cooperative_address"],
            "housing_cooperative_postal_code": deed_dict["cooperative_postal_code"],
            "housing_cooperative_city": deed_dict["cooperative_city"]
        }

        # Build apartment info
        apartment_info = {
            "apartment_address": deed_dict["apartment_address"],
            "apartment_number": deed_dict["apartment_number"],
            "apartment_postal_code": deed_dict["apartment_postal_code"],
            "apartment_city": deed_dict["apartment_city"]
        }

        # Convert housing cooperative signers
        housing_cooperative_signers = [
            {
                "administrator_name": signer["administrator_name"],
                "administrator_person_number": signer["administrator_person_number"],
                "administrator_email": signer["administrator_email"]
            }
            for signer in deed_dict.get("housing_cooperative_signers", [])
        ]

        # Convert borrowers
        borrowers = [
            {
                "name": borrower["name"],
                "person_number": borrower["person_number"],
                "email": borrower["email"],
                "ownership_percentage": borrower["ownership_percentage"]
            }
            for borrower in deed_dict.get("borrowers", [])
        ]

        # Assembling final payload
        deed_data = {
            "credit_numbers": credit_numbers,
            "housing_cooperative_info": housing_cooperative_info,
            "apartment_info": apartment_info,
            "housing_cooperative_signers": housing_cooperative_signers,
            "borrowers": borrowers,
            "is_accounting_firm": deed_dict.get("is_accounting_firm", False),
            "has_existing_mortgages": deed_dict.get("has_existing_mortgages", False),
            "existing_mortgage_bank": deed_dict.get("existing_mortgage_bank", ""),
            "existing_mortgage_date": deed_dict.get("existing_mortgage_date", ""),
            "notes": deed_dict.get("notes", "")
        }

        return deed_data
        
    except Exception as e:
        logger.error(f"Error transforming deed data: {str(e)}")
        raise ValueError(f"Failed to transform deed data: {str(e)}")

# @router.get(
#     "",
#     response_model=List[MortgageDeedResponse],
#     summary="List and filter mortgage deeds",
#     description="""
#     Retrieves a list of mortgage deeds with optional filtering and sorting.
    
#     Supports filtering by:
#     - Status
#     - Housing cooperative
#     - Creation date range
#     - Borrower's person number
#     - Housing cooperative name
#     - Apartment number
#     - Credit numbers (comma-separated list)
    
#     Results are paginated and include pagination headers:
#     - X-Total-Count: Total number of records
#     - X-Total-Pages: Total number of pages
#     - X-Current-Page: Current page number
#     - X-Page-Size: Number of records per page
    
#     Results can be sorted by created_at, status, or apartment_number.
#     """
# )
# async def list_mortgage_deeds(
#     response: Response,
#     deed_status: Optional[str] = Query(None, description="Filter by deed status (e.g., CREATED, PENDING_SIGNATURE, COMPLETED)"),
#     housing_cooperative_id: Optional[int] = Query(None, description="Filter by housing cooperative ID"),
#     bank_id: Optional[int] = Query(None, description="Filter by bank ID"),
#     created_after: Optional[datetime] = Query(None, description="Filter by creation date after (ISO format)"),
#     created_before: Optional[datetime] = Query(None, description="Filter by creation date before (ISO format)"),
#     borrower_person_number: Optional[str] = Query(None, pattern=r'^\d{12}$', description="Filter by borrower's person number (12 digits)"),
#     housing_cooperative_name: Optional[str] = Query(None, description="Filter by housing cooperative name (partial match)"),
#     apartment_number: Optional[str] = Query(None, description="Filter by exact apartment number"),
#     credit_numbers: Optional[str] = Query(None, description="Filter by comma-separated list of credit numbers"),
#     sort_by: Optional[str] = Query(None, description="Sort field (created_at, status, apartment_number)"),
#     sort_order: Optional[str] = Query("asc", pattern="^(asc|desc)$", description="Sort order (asc or desc)"),
#     page: int = Query(1, ge=1, description="Page number"),
#     page_size: int = Query(50, le=100, description="Records per page (max 100)"),
#     current_user: dict = Depends(get_current_user),
#     supabase: SupabaseClient = Depends(get_supabase)
# ) -> List[MortgageDeedResponse]:
#     """
#     List and filter mortgage deeds with pagination.
    
#     Args:
#         deed_status: Filter by deed status
#         housing_cooperative_id: Filter by housing cooperative
#         bank_id: Filter by bank ID
#         created_after: Filter by creation date after
#         created_before: Filter by creation date before
#         borrower_person_number: Filter by borrower's person number
#         housing_cooperative_name: Filter by housing cooperative name
#         apartment_number: Filter by apartment number
#         credit_numbers: Filter by comma-separated list of credit numbers
#         sort_by: Field to sort by
#         sort_order: Sort direction
#         page: Page number (1-based)
#         page_size: Records per page
#         current_user: Current authenticated user
#         supabase: Supabase client
        
#     Returns:
#         List of mortgage deeds matching filters
        
#     Raises:
#         HTTPException: If query fails
#     """
    
#     try:
#         # Validate sort field if provided
#         valid_sort_fields = {'created_at', 'status', 'apartment_number'}
#         if sort_by and sort_by not in valid_sort_fields:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}"
#             )
        
#         # Build base query
#         query = supabase.table('mortgage_deeds').select(
#             "*, borrowers(*), housing_cooperative:housing_cooperatives(*), housing_cooperative_signers(*)"
#         )
        
#         # Always filter by current user's bank_id
#         query = query.eq('bank_id', current_user["bank_id"])
        
#         # Apply filters
#         if deed_status:
#             query = query.eq('status', deed_status)
#         if housing_cooperative_id:
#             query = query.eq('housing_cooperative_id', housing_cooperative_id)
#         if created_after:
#             query = query.gte('created_at', created_after.isoformat())
#         if created_before:
#             query = query.lte('created_at', created_before.isoformat())
#         if apartment_number:
#             query = query.eq('apartment_number', apartment_number)
#         if housing_cooperative_name:
#             query = query.ilike('housing_cooperatives.name', f'%{housing_cooperative_name}%')
#         if credit_numbers:
#             credit_number_list = [cn.strip() for cn in credit_numbers.split(',')]
#             query = query.in_('credit_number', credit_number_list)
        
#         # Handle borrower person number filter
#         if borrower_person_number:
#             borrower_deeds = await handle_supabase_operation(
#                 operation_name="fetch deeds by borrower",
#                 operation=supabase.table('borrowers')
#                     .select('deed_id')
#                     .eq('person_number', borrower_person_number)
#                     .execute(),
#                 error_msg="Failed to fetch deeds by borrower"
#             )
            
#             if borrower_deeds.data:
#                 deed_ids = [b['deed_id'] for b in borrower_deeds.data]
#                 query = query.in_('id', deed_ids)
#             else:
#                 return []
        
#         # Get total count for pagination
#         count_query = supabase.table('mortgage_deeds')
#         # Build count query with filters
#         count_query = count_query.select("id")
#         count_query = count_query.eq('bank_id', current_user["bank_id"])
#         if deed_status:
#             count_query = count_query.eq('status', deed_status)
#         if housing_cooperative_id:
#             count_query = count_query.eq('housing_cooperative_id', housing_cooperative_id)
#         if created_after:
#             count_query = count_query.gte('created_at', created_after.isoformat())
#         if created_before:
#             count_query = count_query.lte('created_at', created_before.isoformat())
#         if apartment_number:
#             count_query = count_query.eq('apartment_number', apartment_number)
#         if credit_numbers:
#             credit_number_list = [cn.strip() for cn in credit_numbers.split(',')]
#             count_query = count_query.in_('credit_number', credit_number_list)
        
        
#         # Execute count query
#         count_result = await handle_supabase_operation(
#             operation_name="count mortgage deeds",
#             operation=count_query.execute(),
#             error_msg="Failed to count mortgage deeds"
#         )
        
#         total_count = len(count_result.data)
#         total_pages = (total_count + page_size - 1) // page_size
        
#         # Apply sorting
#         if sort_by:
#             order_expression = sort_by
#             query = query.order(order_expression)
        
#         # Apply pagination
#         start = (page - 1) * page_size
#         query = query.range(start, start + page_size - 1)
        
#         # Execute final query
#         result = await handle_supabase_operation(
#             operation_name="list mortgage deeds",
#             operation=query.execute(),
#             error_msg="Failed to fetch mortgage deeds"
#         )
        
#         # Set pagination headers
#         response.headers["X-Total-Count"] = str(total_count)
#         response.headers["X-Total-Pages"] = str(total_pages)
#         response.headers["X-Current-Page"] = str(page)
#         response.headers["X-Page-Size"] = str(page_size)
        
#         if not result.data:
#             return []
        
#         return [MortgageDeedResponse(**deed) for deed in result.data]
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error("Error in list_mortgage_deeds: %s", str(e), exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to fetch mortgage deeds"
#         )

# @router.get(
#     "/{deed_id}",
#     response_model=MortgageDeedResponse,
#     summary="Get a specific mortgage deed",
#     description="""
#     Retrieves detailed information about a specific mortgage deed by its ID.
    
#     Only accessible by:
#     - Borrowers listed on the deed
#     - Housing cooperative administrators
    
#     Returns the complete deed data including:
#     - Basic deed information
#     - Associated borrowers
#     - Housing cooperative details
#     """
# )
# async def get_mortgage_deed(
#     deed_id: int = Path(..., description="The ID of the mortgage deed to retrieve"),
#     current_user: dict = Depends(get_current_user),
#     supabase: SupabaseClient = Depends(get_supabase)
# ) -> MortgageDeedResponse:
#     """
#     Get a specific mortgage deed by ID.
    
#     Args:
#         deed_id: ID of the deed to retrieve
#         current_user: Current authenticated user
#         supabase: Supabase client
        
#     Returns:
#         Complete deed data with relations
        
#     Raises:
#         HTTPException: If deed not found or user lacks access
#     """
#     # Fetch deed with relations
#     deed = await get_deed_with_relations(supabase, deed_id)
    
#     # Verify user has access
#     await verify_deed_access(deed, current_user)
    
#     return MortgageDeedResponse(**deed)

# @router.put(
#     "/{deed_id}",
#     response_model=MortgageDeedResponse,
#     summary="Update a mortgage deed",
#     description="""
#     Updates an existing mortgage deed.
    
#     Supports:
#     - Partial updates - only provided fields will be updated
#     - Complete borrower replacement - existing borrowers will be replaced with the new list
    
#     An audit log entry will be created for the update.
#     Only housing cooperative administrators can update deeds.
#     """
# )
# async def update_mortgage_deed(
#     deed_id: int = Path(..., description="The ID of the mortgage deed to update"),
#     deed_update: MortgageDeedUpdate = ...,
#     current_user: dict = Depends(get_current_user),
#     supabase: SupabaseClient = Depends(get_supabase)
# ) -> MortgageDeedResponse:
#     """
#     Update an existing mortgage deed.
    
#     Args:
#         deed_id: ID of the deed to update
#         deed_update: Update data
#         current_user: Current authenticated user
#         supabase: Supabase client
        
#     Returns:
#         Updated deed with all relations
        
#     Raises:
#         HTTPException: If update fails or user lacks permissions
#     """
#     # Fetch current deed to verify access
#     current_deed = await get_deed_with_relations(supabase, deed_id)
#     await verify_deed_access(current_deed, current_user)
    
#     # Prepare update data
#     update_data = {k: v for k, v in deed_update.model_dump().items() 
#                   if v is not None and k not in ['borrowers', 'housing_cooperative_signers']}
    
#     if not update_data and not deed_update.borrowers and not deed_update.housing_cooperative_signers:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="No valid update data provided"
#         )
    
#     # Update deed if there are changes
#     if update_data:
#         result = await handle_supabase_operation(
#             operation_name=f"update deed {deed_id}",
#             operation=supabase.table('mortgage_deeds')
#                 .update(update_data)
#                 .eq('id', deed_id)
#                 .execute(),
#             error_msg="Failed to update mortgage deed"
#         )
        
#         # Create audit log for deed update
#         await create_audit_log(
#             supabase,
#             deed_id,  # entity_id is the deed_id
#             "DEED_UPDATED",
#             current_user["id"],
#             f"Updated mortgage deed for apartment {current_deed['apartment_number']} at {current_deed['apartment_address']} (credit number: {current_deed['credit_number']})",
#             deed_id=deed_id
#         )
    
#     # Handle borrower updates if provided
#     if deed_update.borrowers is not None:
#         # Get existing borrowers
#         existing_borrowers = await handle_supabase_operation(
#             operation_name=f"fetch existing borrowers for deed {deed_id}",
#             operation=supabase.table('borrowers')
#                 .select('*')
#                 .eq('deed_id', deed_id)
#                 .execute(),
#             error_msg="Failed to fetch existing borrowers"
#         )
        
#         # Create dictionaries for comparison
#         existing_borrowers_dict = {
#             b['person_number']: b for b in existing_borrowers.data
#         }
#         new_borrowers_dict = {
#             b.person_number: b.model_dump() for b in deed_update.borrowers
#         }
        
#         # Find borrowers to remove (in existing but not in new)
#         borrowers_to_remove = [
#             b for pn, b in existing_borrowers_dict.items()
#             if pn not in new_borrowers_dict
#         ]
        
#         # Find borrowers to add (in new but not in existing)
#         borrowers_to_add = [
#             b for pn, b in new_borrowers_dict.items()
#             if pn not in existing_borrowers_dict
#         ]
        
#         # Find borrowers to update (in both but with different details)
#         borrowers_to_update = []
#         for pn, new_b in new_borrowers_dict.items():
#             if pn in existing_borrowers_dict:
#                 existing_b = existing_borrowers_dict[pn]
#                 if (existing_b['name'] != new_b['name'] or 
#                     float(existing_b['ownership_percentage']) != float(new_b['ownership_percentage'])):
#                     borrowers_to_update.append(new_b)
        
#         # Remove borrowers that are no longer present
#         if borrowers_to_remove:
#             for borrower in borrowers_to_remove:
#                 # Create audit log for each borrower removal
#                 await create_audit_log(
#                     supabase,
#                     borrower["id"],  # entity_id is the borrower's ID
#                     "BORROWER_REMOVED",
#                     current_user["id"],
#                     f"Removed borrower {borrower['name']} (person number: {borrower['person_number']}) from mortgage deed {deed_id}",
#                     deed_id=deed_id
#                 )
            
#             await handle_supabase_operation(
#                 operation_name=f"delete removed borrowers for deed {deed_id}",
#                 operation=supabase.table('borrowers')
#                     .delete()
#                     .in_('person_number', [b['person_number'] for b in borrowers_to_remove])
#                     .eq('deed_id', deed_id)
#                     .execute(),
#                 error_msg="Failed to delete removed borrowers"
#             )
        
#         # Update existing borrowers that have changes
#         if borrowers_to_update:
#             for borrower in borrowers_to_update:
#                 existing_b = existing_borrowers_dict[borrower['person_number']]
#                 update_data = {
#                     'name': borrower['name'],
#                     'ownership_percentage': float(borrower['ownership_percentage'])
#                 }
                
#                 await handle_supabase_operation(
#                     operation_name=f"update borrower for deed {deed_id}",
#                     operation=supabase.table('borrowers')
#                         .update(update_data)
#                         .eq('deed_id', deed_id)
#                         .eq('person_number', borrower['person_number'])
#                         .execute(),
#                     error_msg="Failed to update borrower"
#                 )
                
#                 # Create audit log for borrower update
#                 await create_audit_log(
#                     supabase,
#                     existing_b["id"],  # entity_id is the borrower's ID
#                     "BORROWER_UPDATED",
#                     current_user["id"],
#                     f"Updated borrower {borrower['name']} (person number: {borrower['person_number']}) with new ownership percentage: {borrower['ownership_percentage']}%",
#                     deed_id=deed_id
#                 )
        
#         # Add new borrowers
#         if borrowers_to_add:
#             borrower_data = [
#                 {
#                     **borrower,
#                     'deed_id': deed_id,
#                     'ownership_percentage': float(borrower['ownership_percentage'])
#                 }
#                 for borrower in borrowers_to_add
#             ]
            
#             new_borrowers = await handle_supabase_operation(
#                 operation_name=f"add new borrowers to deed {deed_id}",
#                 operation=supabase.table('borrowers')
#                     .insert(borrower_data)
#                     .execute(),
#                 error_msg="Failed to add new borrowers"
#             )
            
#             # Create audit log for each new borrower
#             for borrower in new_borrowers.data:
#                 await create_audit_log(
#                     supabase,
#                     borrower["id"],  # entity_id is the borrower's ID
#                     "BORROWER_ADDED",
#                     current_user["id"],
#                     f"Added borrower {borrower['name']} (person number: {borrower['person_number']}) with {borrower['ownership_percentage']}% ownership",
#                     deed_id=deed_id
#                 )

#     # Handle housing cooperative signer updates if provided
#     if deed_update.housing_cooperative_signers is not None:
#         # Get existing signers
#         existing_signers = await handle_supabase_operation(
#             operation_name=f"fetch existing cooperative signers for deed {deed_id}",
#             operation=supabase.table('housing_cooperative_signers')
#                 .select('*')
#                 .eq('mortgage_deed_id', deed_id)
#                 .execute(),
#             error_msg="Failed to fetch existing cooperative signers"
#         )
        
#         # Create dictionaries for comparison
#         existing_signers_dict = {
#             s['administrator_person_number']: s for s in existing_signers.data
#         }
#         new_signers_dict = {
#             s.administrator_person_number: s.model_dump() for s in deed_update.housing_cooperative_signers
#         }
        
#         # Find signers to remove (in existing but not in new)
#         signers_to_remove = [
#             s for pn, s in existing_signers_dict.items()
#             if pn not in new_signers_dict
#         ]
        
#         # Find signers to add (in new but not in existing)
#         signers_to_add = [
#             s for pn, s in new_signers_dict.items()
#             if pn not in existing_signers_dict
#         ]
        
#         # Find signers to update (in both but with different details)
#         signers_to_update = []
#         for pn, new_s in new_signers_dict.items():
#             if pn in existing_signers_dict:
#                 existing_s = existing_signers_dict[pn]
#                 if existing_s['administrator_name'] != new_s['administrator_name']:
#                     signers_to_update.append(new_s)
        
#         # Remove signers that are no longer present
#         if signers_to_remove:
#             for signer in signers_to_remove:
#                 # Create audit log for each signer removal
#                 await create_audit_log(
#                     supabase,
#                     signer["id"],  # entity_id is the signer's ID
#                     "COOPERATIVE_SIGNER_REMOVED",
#                     current_user["id"],
#                     f"Removed cooperative signer {signer['administrator_name']} (person number: {signer['administrator_person_number']}) from mortgage deed {deed_id}",
#                     deed_id=deed_id
#                 )
            
#             await handle_supabase_operation(
#                 operation_name=f"delete removed cooperative signers for deed {deed_id}",
#                 operation=supabase.table('housing_cooperative_signers')
#                     .delete()
#                     .in_('administrator_person_number', [s['administrator_person_number'] for s in signers_to_remove])
#                     .eq('mortgage_deed_id', deed_id)
#                     .execute(),
#                 error_msg="Failed to delete removed cooperative signers"
#             )
        
#         # Update existing signers that have changes
#         if signers_to_update:
#             for signer in signers_to_update:
#                 existing_s = existing_signers_dict[signer['administrator_person_number']]
#                 update_data = {
#                     'administrator_name': signer['administrator_name']
#                 }
                
#                 await handle_supabase_operation(
#                     operation_name=f"update cooperative signer for deed {deed_id}",
#                     operation=supabase.table('housing_cooperative_signers')
#                         .update(update_data)
#                         .eq('mortgage_deed_id', deed_id)
#                         .eq('administrator_person_number', signer['administrator_person_number'])
#                         .execute(),
#                     error_msg="Failed to update cooperative signer"
#                 )
                
#                 # Create audit log for signer update
#                 await create_audit_log(
#                     supabase,
#                     existing_s["id"],  # entity_id is the signer's ID
#                     "COOPERATIVE_SIGNER_UPDATED",
#                     current_user["id"],
#                     f"Updated cooperative signer {signer['administrator_name']} (person number: {signer['administrator_person_number']})",
#                     deed_id=deed_id
#                 )
        
#         # Add new signers
#         if signers_to_add:
#             signer_data = [
#                 {
#                     **signer,
#                     'mortgage_deed_id': deed_id
#                 }
#                 for signer in signers_to_add
#             ]
            
#             new_signers = await handle_supabase_operation(
#                 operation_name=f"add new cooperative signers to deed {deed_id}",
#                 operation=supabase.table('housing_cooperative_signers')
#                     .insert(signer_data)
#                     .execute(),
#                 error_msg="Failed to add new cooperative signers"
#             )
            
#             # Create audit log for each new signer
#             for signer in new_signers.data:
#                 await create_audit_log(
#                     supabase,
#                     signer["id"],  # entity_id is the signer's ID
#                     "COOPERATIVE_SIGNER_ADDED",
#                     current_user["id"],
#                     f"Added cooperative signer {signer['administrator_name']} (person number: {signer['administrator_person_number']})",
#                     deed_id=deed_id
#                 )
    
#     # Fetch and return updated deed
#     updated_deed = await get_deed_with_relations(
#         supabase,
#         deed_id,
#         "Failed to fetch updated deed"
#     )
    
#     return MortgageDeedResponse(**updated_deed)

# @router.delete(
#     "/{deed_id}",
#     status_code=status.HTTP_204_NO_CONTENT,
#     summary="Delete a mortgage deed",
#     description="""
#     Deletes a mortgage deed and all associated data.
    
#     This operation:
#     - Deletes all associated borrowers
#     - Creates a final audit log entry
#     - Removes the deed itself
    
#     This operation cannot be undone.
#     Only housing cooperative administrators can delete deeds.
#     """
# )
# async def delete_mortgage_deed(
#     deed_id: int = Path(..., description="The ID of the mortgage deed to delete"),
#     current_user: dict = Depends(get_current_user),
#     supabase: SupabaseClient = Depends(get_supabase)
# ):
#     """
#     Delete a mortgage deed and its associated data.
    
#     Args:
#         deed_id: ID of the deed to delete
#         current_user: Current authenticated user
#         supabase: Supabase client
        
#     Raises:
#         HTTPException: If deletion fails or user lacks permissions
#     """
#     # Fetch current deed to verify access
#     current_deed = await get_deed_with_relations(supabase, deed_id)
#     await verify_deed_access(current_deed, current_user)
    
#     # Create audit log for deletion initiation
#     await create_audit_log(
#         supabase,
#         deed_id,  # entity_id is the deed_id
#         "DEED_DELETION_INITIATED",
#         current_user["id"],
#         f"Initiated deletion of mortgage deed for apartment {current_deed['apartment_number']} at {current_deed['apartment_address']} (credit number: {current_deed['credit_number']})",
#         deed_id=deed_id
#     )
    
#     # Update audit logs to set deed_id to NULL
#     await handle_supabase_operation(
#         operation_name=f"update audit logs for deed {deed_id}",
#         operation=supabase.table('audit_logs')
#             .update({"deed_id": None})
#             .eq('deed_id', deed_id)
#             .execute(),
#         error_msg="Failed to update audit logs"
#     )
    
#     # Delete borrowers
#     await handle_supabase_operation(
#         operation_name=f"delete borrowers for deed {deed_id}",
#         operation=supabase.table('borrowers')
#             .delete()
#             .eq('deed_id', deed_id)
#             .execute(),
#         error_msg="Failed to delete borrowers"
#     )
    
#     # Delete housing cooperative signers
#     await handle_supabase_operation(
#         operation_name=f"delete cooperative signers for deed {deed_id}",
#         operation=supabase.table('housing_cooperative_signers')
#             .delete()
#             .eq('mortgage_deed_id', deed_id)
#             .execute(),
#         error_msg="Failed to delete cooperative signers"
#     )
    
#     # Delete the deed
#     await handle_supabase_operation(
#         operation_name=f"delete deed {deed_id}",
#         operation=supabase.table('mortgage_deeds')
#             .delete()
#             .eq('id', deed_id)
#             .execute(),
#         error_msg="Failed to delete mortgage deed"
#     )
    
#     # Create final audit log for deed deletion (without deed_id since it's deleted)
#     await create_audit_log(
#         supabase,
#         deed_id,  # entity_id is still the deed_id for historical reference
#         "DEED_DELETED",
#         current_user["id"],
#         f"Deleted mortgage deed for apartment {current_deed['apartment_number']} at {current_deed['apartment_address']} (credit number: {current_deed['credit_number']})"  # Note: no deed_id parameter
#     )

# @router.get(
#     "/pending-signatures/{person_number}",
#     response_model=List[MortgageDeedResponse],
#     summary="Get deeds pending signature",
#     description="""
#     Retrieves all mortgage deeds that are pending signature for a specific person.
    
#     Checks for pending signatures for:
#     - Borrowers listed on the deed
#     - Housing cooperative representatives
    
#     Only returns deeds where the person is authorized to sign and
#     their signature is still pending.
#     """
# )
# async def get_deeds_pending_signature(
#     person_number: str = Path(..., pattern=r'^\d{12}$', description="Person number (12 digits) to check pending signatures for"),
#     current_user: dict = Depends(get_current_user),
#     supabase: SupabaseClient = Depends(get_supabase)
# ) -> List[MortgageDeedResponse]:
#     """
#     Get all mortgage deeds pending signature for a person.
    
#     Args:
#         person_number: Person number to check
#         current_user: Current authenticated user
#         supabase: Supabase client
        
#     Returns:
#         List of deeds pending signature
        
#     Raises:
#         HTTPException: If query fails or user not authorized
#     """
#     # Verify the person number matches the authenticated user
#     user_person_number = current_user.get("user_metadata", {}).get("person_number")
#     if user_person_number != person_number:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to view deeds for this person number"
#         )
    
#     # Query deeds pending signature
#     result = await handle_supabase_operation(
#         operation_name=f"fetch pending signatures for {person_number}",
#         operation=supabase.table('mortgage_deeds')
#             .select("""
#                 *,
#                 borrowers(*),
#                 housing_cooperative:housing_cooperatives(*),
#                 housing_cooperative_signers(*)
#             """)
#             .or_(
#                 f"and(borrowers.person_number.eq.{person_number},borrowers.signature_timestamp.is.null)",
#                 f"and(housing_cooperative_signers.administrator_person_number.eq.{person_number},housing_cooperative_signers.signature_timestamp.is.null)"
#             )
#             .execute(),
#         error_msg="Failed to fetch pending signatures"
#     )
    
#     if not result.data:
#         return []
    
#     return [MortgageDeedResponse(**deed) for deed in result.data]

# Helper Functions
# async def get_deed_with_relations(
#     supabase: SupabaseClient,
#     deed_id: int,
#     error_msg: str = "Mortgage deed not found"
# ) -> dict:
#     """
#     Fetch a mortgage deed with its related data.
    
#     Args:
#         supabase: Supabase client
#         deed_id: ID of the deed to fetch
#         error_msg: Custom error message if deed not found
        
#     Returns:
#         Complete deed data with relations
        
#     Raises:
#         HTTPException: If deed not found or other errors occur
#     """
#     result = await handle_supabase_operation(
#         operation_name=f"fetch deed {deed_id} with relations",
#         operation=supabase.table('mortgage_deeds')
#             .select("*, borrowers(*), housing_cooperative:housing_cooperatives(*), housing_cooperative_signers(*)")
#             .eq('id', deed_id)
#             .single()
#             .execute(),
#         error_msg=error_msg
#     )
    
#     if not result.data:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
    
#     return result.data

# async def verify_deed_access(deed: dict, current_user: dict) -> None:
#     """
#     Verify user has access to the deed.
    
#     Args:
#         deed: Deed data with relations
#         current_user: Current authenticated user
        
#     Raises:
#         HTTPException: If user doesn't have access
#     """
#     user_person_number = current_user.get("user_metadata", {}).get("person_number")
#     user_bank_id = current_user.get("user_metadata", {}).get("bank_id")
    
#     is_borrower = any(b["person_number"] == user_person_number for b in deed["borrowers"])
#     is_admin = deed["housing_cooperative"]["administrator_person_number"] == user_person_number
#     is_bank_user = user_bank_id and str(user_bank_id) == str(deed["bank_id"])
    
#     if not (is_borrower or is_admin or is_bank_user):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access this deed"
#         )
