from typing import List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
import logging
from api.schemas.mortgage_deed import (
    MortgageDeedResponse,
    AuditLogResponse,
    DeedStatus,
    SigningStatus,
    SignRequest,
    SignResponse
)
from api.config import get_supabase, get_settings
from api.dependencies.auth import get_current_user
from api.utils.email_utils import send_email
from api.utils.audit import create_audit_log
from api.utils.template_utils import render_template
from api.utils.supabase_utils import handle_supabase_operation
from supabase._async.client import AsyncClient as SupabaseClient
from fastapi.responses import JSONResponse
# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["signing"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"},
        409: {"description": "Conflict with existing resource"},
        500: {"description": "Internal server error"}
    }
)

# Helper Functions
async def notify_parties(
    deed_id: int,
    supabase: SupabaseClient,
    settings,
    background_tasks: BackgroundTasks
) -> bool:
    """
    Notify all relevant parties about deed signing status changes.
    
    Args:
        deed_id: ID of the mortgage deed
        supabase: Supabase client instance
        settings: Application settings
        background_tasks: FastAPI background tasks handler
        
    Returns:
        bool: True if all notifications were sent successfully
        
    Raises:
        HTTPException: If deed is not found
    """
    result = await handle_supabase_operation(
        operation_name=f"fetch deed {deed_id} with related data",
        operation=supabase.table("mortgage_deeds").select(
            "*, borrowers(*), housing_cooperatives!inner(*)"
        ).eq("id", deed_id).single().execute(),
        error_msg="Failed to fetch deed details"
    )
    
    deed = result.data
    all_emails_sent = True
    
    # Notify borrowers
    for borrower in deed["borrowers"]:
        context = {
            "borrower_name": borrower['name'],
            "apartment_number": deed['apartment_number'],
            "apartment_address": deed['apartment_address'],
            "from_name": settings.EMAILS_FROM_NAME
        }
        email_html = render_template("borrower_sign.html", context)
        
        success = await send_email(
            borrower["email"],
            "Pantbrev redo för signering",
            email_html,
            settings
        )
        if not success:
            all_emails_sent = False
            logger.error(f"Failed to send email to borrower {borrower['email']}")
    
    # Notify housing cooperative administrator
    coop = deed["housing_cooperatives"]
    admin_context = {
        "admin_name": coop['administrator_name'],
        "apartment_number": deed['apartment_number'],
        "apartment_address": deed['apartment_address'],
        "from_name": settings.EMAILS_FROM_NAME
    }
    admin_email_html = render_template("admin_sign.html", admin_context)
    
    success = await send_email(
        coop["administrator_email"],
        "Pantbrev redo för bostadsrättsföreningens godkännande",
        admin_email_html,
        settings
    )
    if not success:
        all_emails_sent = False
        logger.error(f"Failed to send email to housing cooperative administrator {coop['administrator_email']}")
    
    return all_emails_sent

async def verify_all_borrowers_signed(deed_id: int, supabase: SupabaseClient) -> bool:
    """
    Check if all borrowers have signed the deed.
    
    Args:
        deed_id: ID of the mortgage deed
        supabase: Supabase client instance
        
    Returns:
        bool: True if all borrowers have signed, False otherwise
    """
    result = await handle_supabase_operation(
        operation_name=f"check borrower signatures for deed {deed_id}",
        operation=supabase.table("borrowers").select("signature_timestamp").eq("deed_id", deed_id).execute(),
        error_msg="Failed to verify borrower signatures"
    )
    
    return all(borrower["signature_timestamp"] is not None for borrower in result.data)

async def verify_all_admins_signed(deed_id: int, supabase: SupabaseClient) -> bool:
    """
    Check if all required administrators have signed the deed.
    
    Args:
        deed_id: ID of the mortgage deed
        supabase: Supabase client instance
        
    Returns:
        bool: True if all administrators have signed, False otherwise
    """
    result = await handle_supabase_operation(
        operation_name=f"check admin signatures for deed {deed_id}",
        operation=supabase.table("housing_cooperative_signers").select("signature_timestamp").eq("mortgage_deed_id", deed_id).execute(),
        error_msg="Failed to verify administrator signatures"
    )
    
    return all(signer["signature_timestamp"] is not None for signer in result.data)

async def update_deed_status(deed_id: int, new_status: DeedStatus, user_id: str, supabase: SupabaseClient):
    """
    Update the deed status and create an audit log entry.
    
    Args:
        deed_id: ID of the mortgage deed
        new_status: New status to set
        user_id: ID of the user making the change
        supabase: Supabase client instance
        
    Raises:
        HTTPException: If deed is not found or status transition is invalid
    """
    await handle_supabase_operation(
        operation_name=f"update deed {deed_id} status to {new_status}",
        operation=supabase.table("mortgage_deeds").update({
            "status": new_status
        }).eq("id", deed_id).execute(),
        error_msg=f"Failed to update deed status to {new_status}"
    )
    
    await create_audit_log(
        supabase,
        deed_id,
        f"STATUS_CHANGED_TO_{new_status}",
        user_id,
        f"Deed status changed to {new_status}",
        deed_id
    )

async def notify_administrators_for_signing(deed_id: int, supabase: SupabaseClient, settings) -> bool:
    """
    Notify administrators that a deed is ready for their signature.
    """
    result = await handle_supabase_operation(
        operation_name=f"fetch deed {deed_id} with cooperative details",
        operation=supabase.table("mortgage_deeds").select(
            "*, borrowers(*), housing_cooperatives!inner(*)"
        ).eq("id", deed_id).single().execute(),
        error_msg="Failed to fetch deed details"
    )
    
    deed = result.data
    coop = deed["housing_cooperatives"]
    
    context = {
        "admin_name": coop['administrator_name'],
        "from_name": settings.EMAILS_FROM_NAME,
        "deed": {
            "reference_number": deed["credit_number"],
            "apartment_number": deed["apartment_number"],
            "apartment_address": deed["apartment_address"],
            "cooperative_name": coop["name"],
            "borrowers": deed["borrowers"]
        }
    }
    
    return await send_email(
        coop["administrator_email"],
        "Pantbrev redo för bostadsrättsföreningens godkännande",
        "admin_sign.html",
        context,
        settings
    )

async def notify_all_parties_completion(deed_id: int, supabase: SupabaseClient, settings) -> bool:
    """
    Notify all parties when the deed is fully signed and completed.
    """
    result = await handle_supabase_operation(
        operation_name=f"fetch deed {deed_id} with related data",
        operation=supabase.table("mortgage_deeds").select(
            "*, borrowers(*), housing_cooperatives!inner(*)"
        ).eq("id", deed_id).single().execute(),
        error_msg="Failed to fetch deed details"
    )
    
    deed = result.data
    coop = deed["housing_cooperatives"]
    
    # Get administrator signature timestamp
    admin_result = await handle_supabase_operation(
        operation_name=f"fetch admin signature for deed {deed_id}",
        operation=supabase.table("housing_cooperative_signers")
            .select("signature_timestamp")
            .eq("mortgage_deed_id", deed_id)
            .single()
            .execute(),
        error_msg="Failed to fetch admin signature"
    )
    
    context = {
        "from_name": settings.EMAILS_FROM_NAME,
        "deed": {
            "reference_number": deed["credit_number"],
            "apartment_number": deed["apartment_number"],
            "apartment_address": deed["apartment_address"],
            "cooperative_name": coop["name"],
            "administrator_name": coop["administrator_name"],
            "administrator_signature_timestamp": admin_result.data["signature_timestamp"] if admin_result.data else None,
            "borrowers": deed["borrowers"]
        }
    }
    
    # Notify all parties
    all_emails_sent = True
    recipients = [borrower["email"] for borrower in deed["borrowers"]]
    recipients.append(coop["administrator_email"])
    
    for recipient in recipients:
        success = await send_email(
            recipient,
            "Pantbrev fullständigt signerat",
            "all_signed.html",
            context,
            settings
        )
        if not success:
            all_emails_sent = False
            logger.error(f"Failed to send completion email to {recipient}")
    
    return all_emails_sent

# Endpoints
@router.post(
    "/deeds/{deed_id}/send-for-signing",
    response_model=MortgageDeedResponse,
    summary="Initiate deed signing process",
    description="""
    Initiates the signing process for a mortgage deed.
    
    This endpoint:
    1. Updates the deed status to PENDING_BORROWER_SIGNATURE
    2. Creates an audit log entry
    3. Sends email notifications to all borrowers
    
    The signing process follows this flow:
    CREATED -> PENDING_BORROWER_SIGNATURE -> PENDING_HOUSING_COOPERATIVE_SIGNATURE -> COMPLETED
    """
)
async def send_for_signing(
    deed_id: int,
    # background_tasks: BackgroundTasks,
    supabase: SupabaseClient = Depends(get_supabase),
    settings = Depends(get_settings)
) -> MortgageDeedResponse:
    # Fetch deed details
    print("a-----------------------------------------1")
    deed_result = await handle_supabase_operation(
        operation_name=f"fetch deed {deed_id}",
        operation=supabase.table("mortgage_deeds").select(
            "*, borrowers(*), housing_cooperative:housing_cooperatives(*)"
        ).eq("id", deed_id).single().execute(),
        error_msg="Failed to fetch deed details"
    )
    
    deed = deed_result.data
    
    # Create audit log for signing initiation
    await create_audit_log(
        supabase,
        deed_id,
        "SIGNING_INITIATED",
        deed["created_by"],
        f"Initiated signing process for mortgage deed {deed_id} (apartment {deed['apartment_number']} at {deed['apartment_address']})"
    )
    
    # Update deed status
    await update_deed_status(
        deed_id,
        "PENDING_BORROWER_SIGNATURE",
        deed["created_by"],
        supabase
    )
    
    # Send notifications to borrowers only
    all_emails_sent = True
    for borrower in deed["borrowers"]:
        context = {
            "borrower_name": borrower['name'],
            "deed": {
                "reference_number": deed["credit_number"],
                "apartment_number": deed["apartment_number"],
                "apartment_address": deed["apartment_address"],
                "cooperative_name": deed["housing_cooperative"]["name"],
                "borrowers": deed["borrowers"]
            },
            "signing_url": f"{settings.BACKEND_URL}/deeds/{deed_id}/signatures/borrower",
            "from_name": settings.EMAILS_FROM_NAME
        }
        
        success = await send_email(
            recipient_email=borrower["email"],
            subject="Pantbrev redo för signering",
            template_name="borrower_sign.html",
            template_context=context,
            settings=settings
        )
        if not success:
            all_emails_sent = False
            logger.error(f"Failed to send email to borrower {borrower['email']}")
        print("Borrow sign email sent!!!!!!!!")
    
    if not all_emails_sent:
        logger.warning(f"Some notifications failed to send for deed {deed_id}")
        await create_audit_log(
            supabase,
            deed_id,
            "NOTIFICATION_FAILURE",
            deed["created_by"],
            f"Failed to send some notifications for mortgage deed {deed_id} (apartment {deed['apartment_number']})"
        )
    else:
        await create_audit_log(
            supabase,
            deed_id,
            "NOTIFICATIONS_SENT",
            deed["created_by"],
            f"Successfully sent all notifications for mortgage deed {deed_id} (apartment {deed['apartment_number']})"
        )
        print("create audit log!!!!!!!!!")
    
    # Fetch complete deed data
    complete_result = await handle_supabase_operation(
        operation_name=f"fetch updated deed {deed_id}",
        operation=supabase.table("mortgage_deeds").select(
            "*, borrowers(*), housing_cooperative:housing_cooperatives(*)"
        ).eq("id", deed_id).single().execute(),
        error_msg="Failed to fetch updated deed details"
    )
    print("complete!!!!!!!!!!!!", complete_result.data)
    return JSONResponse(content={"detail": "Signing process initiated successfully"}, status_code=200)

@router.post(
    "/deeds/{deed_id}/signatures/borrower",
    response_model=SignResponse,
    summary="Sign deed as a borrower"
)
async def borrower_sign(
    deed_id: int,
    sign_request: SignRequest,
    background_tasks: BackgroundTasks,
    supabase: SupabaseClient = Depends(get_supabase),
    settings = Depends(get_settings)
) -> SignResponse:
    # Verify deed exists and is in correct status
    deed_result = await handle_supabase_operation(
        operation_name=f"fetch deed {deed_id} status",
        operation=supabase.table("mortgage_deeds").select("status, created_by").eq("id", deed_id).single().execute(),
        error_msg="Failed to fetch deed status"
    )
    
    deed = deed_result.data
    if deed["status"] != "PENDING_BORROWER_SIGNATURE":
        await create_audit_log(
            supabase,
            deed_id,
            "BORROWER_SIGNATURE_INVALID_STATUS",
            deed["created_by"],
            f"Invalid status for borrower signature (current status: {deed['status']}) for mortgage deed {deed_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deed is not in the correct status for borrower signing"
        )
    
    # Check if borrower exists and has not signed
    borrower = await handle_supabase_operation(
        operation_name=f"check borrower signature status",
        operation=supabase.table("borrowers").select("signature_timestamp").eq(
            "deed_id", deed_id
        ).eq("person_number", sign_request.person_number).single().execute(),
        error_msg="Failed to check borrower signature status"
    )
    
    if not borrower.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found for this deed"
        )
    
    if borrower.data["signature_timestamp"] is not None:
        await create_audit_log(
            supabase,
            deed_id,
            "BORROWER_SIGNATURE_DUPLICATE_ATTEMPT",
            deed["created_by"],
            f"Duplicate signature attempt by borrower {sign_request.person_number} for mortgage deed {deed_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Borrower has already signed this deed"
        )
    
    # Update borrower signature timestamp
    await handle_supabase_operation(
        operation_name=f"update borrower signature",
        operation=supabase.table("borrowers").update({
            "signature_timestamp": "now()"
        }).eq("deed_id", deed_id).eq("person_number", sign_request.person_number).execute(),
        error_msg="Failed to update borrower signature"
    )
    
    # Create audit log entry for borrower signing
    await create_audit_log(
        supabase,
        deed_id,
        "BORROWER_SIGNED",
        deed["created_by"],
        f"Borrower {sign_request.person_number} signed mortgage deed {deed_id}"
    )
    
    # Check if all borrowers have signed
    all_signed = await verify_all_borrowers_signed(deed_id, supabase)
    if all_signed:
        await create_audit_log(
            supabase,
            deed_id,
            "ALL_BORROWERS_SIGNED",
            deed["created_by"],
            f"All borrowers have signed mortgage deed {deed_id}"
        )
        
        # Update deed status
        await update_deed_status(
            deed_id,
            "PENDING_HOUSING_COOPERATIVE_SIGNATURE",
            deed["created_by"],
            supabase
        )
        
        # Notify housing cooperative administrators
        await notify_administrators_for_signing(
            deed_id,
            supabase,
            settings
        )
        return SignResponse(
            deed_id=deed_id,
            status="PENDING_HOUSING_COOPERATIVE_SIGNATURE",
            message="All borrowers have signed. Housing cooperative administrators have been notified."
        )
    
    return SignResponse(
        deed_id=deed_id,
        status="PENDING_BORROWER_SIGNATURE",
        message="Signature recorded successfully. Waiting for other borrowers to sign."
    )

@router.post(
    "/{deed_id}/signatures/cooperative-admin",
    response_model=SignResponse,
    summary="Sign deed as a housing cooperative administrator"
)
async def cooperative_admin_sign(
    deed_id: int,
    sign_request: SignRequest,
    background_tasks: BackgroundTasks,
    supabase: SupabaseClient = Depends(get_supabase),
    settings = Depends(get_settings)
) -> SignResponse:
    # Verify deed exists and is in correct status
    deed_result = await handle_supabase_operation(
        operation_name=f"fetch deed {deed_id} with cooperative details",
        operation=supabase.table("mortgage_deeds").select(
            "status, created_by, housing_cooperatives!inner(*)"
        ).eq("id", deed_id).single().execute(),
        error_msg="Failed to fetch deed details"
    )
    
    deed = deed_result.data
    if deed["status"] != "PENDING_HOUSING_COOPERATIVE_SIGNATURE":
        await create_audit_log(
            supabase,
            deed_id,
            "ADMIN_SIGNATURE_INVALID_STATUS",
            deed["created_by"],
            f"Invalid status for administrator signature (current status: {deed['status']}) for mortgage deed {deed_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deed is not in the correct status for administrator signing"
        )
    
    # Verify administrator
    if sign_request.person_number != deed["housing_cooperatives"]["administrator_person_number"]:
        await create_audit_log(
            supabase,
            deed_id,
            "ADMIN_SIGNATURE_WRONG_ADMIN",
            deed["created_by"],
            f"Attempt to sign as wrong administrator with person number {sign_request.person_number} for mortgage deed {deed_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to sign this deed"
        )
    
    # Record administrator signature
    await handle_supabase_operation(
        operation_name=f"update administrator signature",
        operation=supabase.table("housing_cooperative_signers").update({
            "signature_timestamp": "now()"
        }).eq("mortgage_deed_id", deed_id).eq(
            "administrator_person_number", sign_request.person_number
        ).execute(),
        error_msg="Failed to update administrator signature"
    )
    
    # Create audit log entry for administrator signing
    await create_audit_log(
        supabase,
        deed_id,
        "ADMINISTRATOR_SIGNED",
        deed["created_by"],
        f"Administrator {sign_request.person_number} signed mortgage deed {deed_id}"
    )
    
    # Check if all administrators have signed
    all_signed = await verify_all_admins_signed(deed_id, supabase)
    if all_signed:
        await create_audit_log(
            supabase,
            deed_id,
            "ALL_ADMINISTRATORS_SIGNED",
            deed["created_by"],
            f"All administrators have signed mortgage deed {deed_id}"
        )
        
        # Update deed status to completed
        await update_deed_status(
            deed_id,
            "COMPLETED",
            deed["created_by"],
            supabase
        )
        
        # Notify all parties about completion
        await notify_all_parties_completion(
            deed_id,
            supabase,
            settings
        )
        
        return SignResponse(
            deed_id=deed_id,
            status="COMPLETED",
            message="All signatures collected. All parties have been notified."
        )
    
    return SignResponse(
        deed_id=deed_id,
        status="PENDING_HOUSING_COOPERATIVE_SIGNATURE",
        message="Signature recorded successfully. Waiting for other administrators to sign."
    ) 