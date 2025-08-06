import secrets
import logging
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import HTMLResponse
from api.config import get_supabase, get_settings
from api.schemas.signing import SigningTokenCreate, SigningTokenResponse, BorrowerSignRequest, BorrowerSignResponse
from api.utils.supabase_utils import handle_supabase_operation
from supabase._async.client import AsyncClient as SupabaseClient

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["signing"],
    responses={
        404: {"description": "Signing token not found or expired"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)

def generate_signing_token() -> str:
    """Generate a secure random token for signing."""
    return secrets.token_urlsafe(32)

@router.post(
    "/create-token",
    response_model=SigningTokenResponse,
    summary="Create signing token for borrower",
    description="Creates a unique signing token for a borrower to sign a mortgage deed."
)
async def create_signing_token(
    token_data: SigningTokenCreate,
    supabase: SupabaseClient = Depends(get_supabase)
) -> SigningTokenResponse:
    """Create a signing token for a borrower."""
    try:
        # Generate unique token
        token = generate_signing_token()
        
        # Create signing token record
        signing_token_data = {
            "deed_id": token_data.deed_id,
            "borrower_id": token_data.borrower_id,
            "token": token,
            "email": token_data.email,
            "expires_at": token_data.expires_at.isoformat()
        }
        
        result = await handle_supabase_operation(
            operation_name="create signing token",
            operation=supabase.table("signing_tokens").insert(signing_token_data).execute(),
            error_msg="Failed to create signing token"
        )
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to create signing token"
            )
        
        created_token = result.data[0]
        return SigningTokenResponse(**created_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating signing token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create signing token"
        )

@router.get(
    "/verify/{token}",
    response_model=dict,
    summary="Verify signing token",
    description="Verifies a signing token and returns deed information for signing."
)
async def verify_signing_token(
    token: str,
    supabase: SupabaseClient = Depends(get_supabase)
) -> dict:
    """Verify a signing token and return deed information."""
    try:
        # Get signing token
        token_result = await handle_supabase_operation(
            operation_name="fetch signing token",
            operation=supabase.table("signing_tokens")
                .select("*")
                .eq("token", token)
                .single()
                .execute(),
            error_msg="Failed to fetch signing token"
        )
        
        if not token_result.data:
            raise HTTPException(
                status_code=404,
                detail="Signing token not found"
            )
        
        signing_token = token_result.data
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(signing_token["expires_at"].replace("Z", "+00:00"))
        current_time = datetime.now().replace(tzinfo=expires_at.tzinfo)
        if expires_at < current_time:
            raise HTTPException(
                status_code=400,
                detail="Signing token has expired"
            )
        
        # Check if token is already used
        if signing_token["used_at"]:
            raise HTTPException(
                status_code=400,
                detail="Signing token has already been used"
            )
        
        # Get deed and borrower information
        deed_result = await handle_supabase_operation(
            operation_name="fetch deed for signing",
            operation=supabase.table("mortgage_deeds")
                .select("*, housing_cooperative:housing_cooperatives(name, organisation_number, address, city, postal_code), borrowers(id, name, email, person_number, ownership_percentage)")
                .eq("id", signing_token["deed_id"])
                .single()
                .execute(),
            error_msg="Failed to fetch deed information"
        )
        
        if not deed_result.data:
            raise HTTPException(
                status_code=404,
                detail="Deed not found"
            )
        
        deed = deed_result.data
        
        # Find the specific borrower
        borrower = None
        for b in deed.get("borrowers", []):
            if b["id"] == signing_token["borrower_id"]:
                borrower = b
                break
        
        if not borrower:
            raise HTTPException(
                status_code=404,
                detail="Borrower not found"
            )
        
        return {
            "token": token,
            "deed": deed,
            "borrower": borrower,
            "expires_at": signing_token["expires_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying signing token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to verify signing token"
        )

@router.post(
    "/sign",
    response_model=BorrowerSignResponse,
    summary="Sign mortgage deed",
    description="Signs a mortgage deed using a valid signing token."
)
async def sign_mortgage_deed(
    sign_request: BorrowerSignRequest,
    supabase: SupabaseClient = Depends(get_supabase)
) -> BorrowerSignResponse:
    """Sign a mortgage deed using a signing token."""
    try:
        logger.info(f"Processing signing request for token: {sign_request.token[:10]}...")
        
        # Get signing token
        token_result = await handle_supabase_operation(
            operation_name="fetch signing token for signing",
            operation=supabase.table("signing_tokens")
                .select("*")
                .eq("token", sign_request.token)
                .single()
                .execute(),
            error_msg="Failed to fetch signing token"
        )
        
        if not token_result.data:
            logger.error(f"Signing token not found: {sign_request.token[:10]}...")
            raise HTTPException(
                status_code=404,
                detail="Signing token not found"
            )
        
        signing_token = token_result.data
        logger.info(f"Found signing token for deed_id: {signing_token['deed_id']}, borrower_id: {signing_token['borrower_id']}")
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(signing_token["expires_at"].replace("Z", "+00:00"))
        current_time = datetime.now().replace(tzinfo=expires_at.tzinfo)
        if expires_at < current_time:
            logger.error(f"Signing token expired: {sign_request.token[:10]}...")
            raise HTTPException(
                status_code=400,
                detail="Signing token has expired"
            )
        
        # Check if token is already used
        if signing_token["used_at"]:
            logger.error(f"Signing token already used: {sign_request.token[:10]}...")
            raise HTTPException(
                status_code=400,
                detail="Signing token has already been used"
            )
        
        # Mark token as used
        logger.info(f"Marking token as used: {sign_request.token[:10]}...")
        await handle_supabase_operation(
            operation_name="mark token as used",
            operation=supabase.table("signing_tokens")
                .update({"used_at": current_time.isoformat()})
                .eq("token", sign_request.token)
                .execute(),
            error_msg="Failed to mark token as used"
        )
        logger.info(f"Successfully marked token as used: {sign_request.token[:10]}...")
        
        # Check if this is a borrower token or housing cooperative signer token
        # We can determine this by checking the signer_type field
        signer_type = signing_token.get("signer_type", "borrower")
        
        if signer_type == "borrower":
            # Handle borrower signing
            logger.info(f"Processing borrower signing for borrower_id: {signing_token['borrower_id']}")
            
            # Update borrower signature timestamp
            logger.info(f"Updating borrower signature for borrower_id: {signing_token['borrower_id']}")
            await handle_supabase_operation(
                operation_name="update borrower signature",
                operation=supabase.table("borrowers")
                    .update({"signature_timestamp": current_time.isoformat()})
                    .eq("id", signing_token["borrower_id"])
                    .execute(),
                error_msg="Failed to update borrower signature"
            )
            logger.info(f"Successfully updated borrower signature for borrower_id: {signing_token['borrower_id']}")
            
            # Check if all borrowers have signed
            logger.info(f"Checking if all borrowers have signed for deed_id: {signing_token['deed_id']}")
            borrowers_result = await handle_supabase_operation(
                operation_name="fetch all borrowers for deed",
                operation=supabase.table("borrowers")
                    .select("signature_timestamp")
                    .eq("deed_id", signing_token["deed_id"])
                    .execute(),
                error_msg="Failed to fetch borrowers"
            )
            
            all_signed = True
            total_signers = len(borrowers_result.data)
            signed_signers = 0
            
            for borrower in borrowers_result.data:
                if borrower["signature_timestamp"]:
                    signed_signers += 1
                else:
                    all_signed = False
            
            logger.info(f"Borrower signing status: {signed_signers}/{total_signers} borrowers signed")
            
            # Update deed status if all borrowers have signed
            if all_signed:
                logger.info(f"All borrowers have signed. Updating deed status to PENDING_HOUSING_COOPERATIVE_SIGNATURE")
                await handle_supabase_operation(
                    operation_name="update deed status to pending cooperative",
                    operation=supabase.table("mortgage_deeds")
                        .update({"status": "PENDING_HOUSING_COOPERATIVE_SIGNATURE"})
                        .eq("id", signing_token["deed_id"])
                        .execute(),
                    error_msg="Failed to update deed status"
                )
                logger.info(f"Successfully updated deed status to PENDING_HOUSING_COOPERATIVE_SIGNATURE")
            else:
                logger.info(f"Not all borrowers have signed yet. Current status: {signed_signers}/{total_signers}")
            
            # Get borrower information for response
            borrower_result = await handle_supabase_operation(
                operation_name="fetch borrower information",
                operation=supabase.table("borrowers")
                    .select("name, email")
                    .eq("id", signing_token["borrower_id"])
                    .single()
                    .execute(),
                error_msg="Failed to fetch borrower information"
            )
            
            signer_name = borrower_result.data.get("name", "Unknown") if borrower_result.data else "Unknown"
            
        elif signer_type == "housing_cooperative_signer":
            # Handle housing cooperative signer signing
            logger.info(f"Processing housing cooperative signer signing for signer_id: {signing_token['housing_cooperative_signer_id']}")
            
            # Update housing cooperative signer signature timestamp
            logger.info(f"Updating housing cooperative signer signature for signer_id: {signing_token['housing_cooperative_signer_id']}")
            await handle_supabase_operation(
                operation_name="update housing cooperative signer signature",
                operation=supabase.table("housing_cooperative_signers")
                    .update({"signature_timestamp": current_time.isoformat()})
                    .eq("id", signing_token["housing_cooperative_signer_id"])
                    .execute(),
                error_msg="Failed to update housing cooperative signer signature"
            )
            logger.info(f"Successfully updated housing cooperative signer signature for signer_id: {signing_token['housing_cooperative_signer_id']}")
            
            # Check if all housing cooperative signers have signed
            logger.info(f"Checking if all housing cooperative signers have signed for deed_id: {signing_token['deed_id']}")
            signers_result = await handle_supabase_operation(
                operation_name="fetch all housing cooperative signers for deed",
                operation=supabase.table("housing_cooperative_signers")
                    .select("signature_timestamp")
                    .eq("mortgage_deed_id", signing_token["deed_id"])
                    .execute(),
                error_msg="Failed to fetch housing cooperative signers"
            )
            
            all_signed = True
            total_signers = len(signers_result.data)
            signed_signers = 0
            
            for signer in signers_result.data:
                if signer["signature_timestamp"]:
                    signed_signers += 1
                else:
                    all_signed = False
            
            logger.info(f"Cooperative signing status: {signed_signers}/{total_signers} signers signed")
            
            # Update deed status if all housing cooperative signers have signed
            if all_signed:
                logger.info(f"All housing cooperative signers have signed. Updating deed status to COMPLETED")
                await handle_supabase_operation(
                    operation_name="update deed status to completed",
                    operation=supabase.table("mortgage_deeds")
                        .update({"status": "COMPLETED"})
                        .eq("id", signing_token["deed_id"])
                        .execute(),
                    error_msg="Failed to update deed status"
                )
                logger.info(f"Successfully updated deed status to COMPLETED")
            else:
                logger.info(f"Not all housing cooperative signers have signed yet. Current status: {signed_signers}/{total_signers}")
            
            # Get housing cooperative signer information for response
            signer_result = await handle_supabase_operation(
                operation_name="fetch housing cooperative signer information",
                operation=supabase.table("housing_cooperative_signers")
                    .select("administrator_name, administrator_email")
                    .eq("id", signing_token["housing_cooperative_signer_id"])
                    .single()
                    .execute(),
                error_msg="Failed to fetch housing cooperative signer information"
            )
            
            signer_name = signer_result.data.get("administrator_name", "Unknown") if signer_result.data else "Unknown"
            
        else:
            logger.error(f"Invalid signer_type: {signer_type}")
            raise HTTPException(
                status_code=400,
                detail="Invalid signing token type"
            )
        
        logger.info(f"Successfully processed signing for {signer_type}: {signer_name}")
        
        return BorrowerSignResponse(
            success=True,
            message=f"Mortgage deed signed successfully by {signer_name} ({signer_type})",
            deed_id=signing_token["deed_id"],
            borrower_name=signer_name,
            signing_status=f"{signed_signers}/{total_signers} {signer_type}s signed",
            all_signed=all_signed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error signing mortgage deed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sign mortgage deed: {str(e)}"
        )

@router.post(
    "/sign-cooperative",
    response_model=BorrowerSignResponse,
    summary="Sign mortgage deed as housing cooperative",
    description="Signs a mortgage deed as a housing cooperative signer."
)
async def sign_mortgage_deed_cooperative(
    sign_request: BorrowerSignRequest,
    supabase: SupabaseClient = Depends(get_supabase)
) -> BorrowerSignResponse:
    """Sign a mortgage deed as a housing cooperative signer."""
    try:
        logger.info(f"Processing housing cooperative signing request for token: {sign_request.token[:10]}...")
        
        # Get signing token
        token_result = await handle_supabase_operation(
            operation_name="fetch signing token for cooperative signing",
            operation=supabase.table("signing_tokens")
                .select("*")
                .eq("token", sign_request.token)
                .single()
                .execute(),
            error_msg="Failed to fetch signing token"
        )
        
        if not token_result.data:
            logger.error(f"Signing token not found: {sign_request.token[:10]}...")
            raise HTTPException(
                status_code=404,
                detail="Signing token not found"
            )
        
        signing_token = token_result.data
        logger.info(f"Found signing token for deed_id: {signing_token['deed_id']}")
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(signing_token["expires_at"].replace("Z", "+00:00"))
        current_time = datetime.now().replace(tzinfo=expires_at.tzinfo)
        if expires_at < current_time:
            logger.error(f"Signing token expired: {sign_request.token[:10]}...")
            raise HTTPException(
                status_code=400,
                detail="Signing token has expired"
            )
        
        # Check if token is already used
        if signing_token["used_at"]:
            logger.error(f"Signing token already used: {sign_request.token[:10]}...")
            raise HTTPException(
                status_code=400,
                detail="Signing token has already been used"
            )
        
        # Get deed information to find housing cooperative signers
        deed_result = await handle_supabase_operation(
            operation_name="fetch deed for cooperative signing",
            operation=supabase.table("mortgage_deeds")
                .select("*, housing_cooperative_signers(*)")
                .eq("id", signing_token["deed_id"])
                .single()
                .execute(),
            error_msg="Failed to fetch deed information"
        )
        
        if not deed_result.data:
            logger.error(f"Deed not found: {signing_token['deed_id']}")
            raise HTTPException(
                status_code=404,
                detail="Deed not found"
            )
        
        deed = deed_result.data
        
        # Find the housing cooperative signer by email (assuming the token email matches the signer email)
        housing_cooperative_signer = None
        for signer in deed.get("housing_cooperative_signers", []):
            if signer["administrator_email"] == signing_token["email"]:
                housing_cooperative_signer = signer
                break
        
        if not housing_cooperative_signer:
            logger.error(f"Housing cooperative signer not found for email: {signing_token['email']}")
            raise HTTPException(
                status_code=404,
                detail="Housing cooperative signer not found"
            )
        
        # Update housing cooperative signer signature timestamp
        logger.info(f"Updating housing cooperative signer signature for signer_id: {housing_cooperative_signer['id']}")
        await handle_supabase_operation(
            operation_name="update housing cooperative signer signature",
            operation=supabase.table("housing_cooperative_signers")
                .update({"signature_timestamp": current_time.isoformat()})
                .eq("id", housing_cooperative_signer["id"])
                .execute(),
            error_msg="Failed to update housing cooperative signer signature"
        )
        logger.info(f"Successfully updated housing cooperative signer signature for signer_id: {housing_cooperative_signer['id']}")
        
        # Mark token as used
        logger.info(f"Marking token as used: {sign_request.token[:10]}...")
        await handle_supabase_operation(
            operation_name="mark token as used",
            operation=supabase.table("signing_tokens")
                .update({"used_at": current_time.isoformat()})
                .eq("token", sign_request.token)
                .execute(),
            error_msg="Failed to mark token as used"
        )
        logger.info(f"Successfully marked token as used: {sign_request.token[:10]}...")
        
        # Check if all housing cooperative signers have signed
        logger.info(f"Checking if all housing cooperative signers have signed for deed_id: {signing_token['deed_id']}")
        signers_result = await handle_supabase_operation(
            operation_name="fetch all housing cooperative signers for deed",
            operation=supabase.table("housing_cooperative_signers")
                .select("signature_timestamp")
                .eq("mortgage_deed_id", signing_token["deed_id"])
                .execute(),
            error_msg="Failed to fetch housing cooperative signers"
        )
        
        all_signed = True
        total_signers = len(signers_result.data)
        signed_signers = 0
        
        for signer in signers_result.data:
            if signer["signature_timestamp"]:
                signed_signers += 1
            else:
                all_signed = False
        
        logger.info(f"Cooperative signing status: {signed_signers}/{total_signers} signers signed")
        
        # Update deed status if all housing cooperative signers have signed
        if all_signed:
            logger.info(f"All housing cooperative signers have signed. Updating deed status to COMPLETED")
            await handle_supabase_operation(
                operation_name="update deed status to completed",
                operation=supabase.table("mortgage_deeds")
                    .update({"status": "COMPLETED"})
                    .eq("id", signing_token["deed_id"])
                    .execute(),
                error_msg="Failed to update deed status"
            )
            logger.info(f"Successfully updated deed status to COMPLETED")
        else:
            logger.info(f"Not all housing cooperative signers have signed yet. Current status: {signed_signers}/{total_signers}")
        
        logger.info(f"Successfully processed housing cooperative signing for signer: {housing_cooperative_signer['administrator_name']}")
        
        return BorrowerSignResponse(
            success=True,
            message=f"Mortgage deed signed successfully by housing cooperative signer {housing_cooperative_signer['administrator_name']}",
            deed_id=signing_token["deed_id"],
            borrower_name=housing_cooperative_signer["administrator_name"],
            signing_status=f"{signed_signers}/{total_signers} cooperative signers signed",
            all_signed=all_signed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error signing mortgage deed as housing cooperative: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sign mortgage deed as housing cooperative: {str(e)}"
        )

@router.post(
    "/test-email",
    summary="Test email sending",
    description="Test endpoint to verify email sending functionality."
)
async def test_email_sending(
    email: str = Query(..., description="Email address to send test email to"),
    supabase: SupabaseClient = Depends(get_supabase),
    settings = Depends(get_settings)
):
    """Test email sending functionality."""
    try:
        from api.utils.email_utils import send_email
        
        logger.info(f"Testing email sending to {email}")
        
        context = {
            "borrower_name": "Test User",
            "deed": {
                "reference_number": "TEST123",
                "apartment_number": "A1",
                "apartment_address": "Test Address 1",
                "cooperative_name": "Test Cooperative",
                "amount": "1,000,000 SEK",
                "created_date": "2024-01-01"
            },
            "signing_url": "https://example.com/sign/test-token",
            "from_name": settings.EMAILS_FROM_NAME,
            "current_year": 2024
        }
        
        success = await send_email(
            recipient_email=email,
            subject="Test Email - Mortgage Deed System",
            template_name="borrower_notification.html",
            template_context=context,
            settings=settings
        )
        
        if success:
            return {"message": f"Test email sent successfully to {email}"}
        else:
            return {"message": f"Failed to send test email to {email}"}
            
    except Exception as e:
        logger.error(f"Error in test email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Test email failed: {str(e)}"
        )

@router.get(
    "/test-template",
    summary="Test template rendering",
    description="Test endpoint to verify template rendering functionality."
)
async def test_template_rendering(
    settings = Depends(get_settings)
):
    """Test template rendering functionality."""
    try:
        from api.utils.template_utils import render_template
        
        logger.info("Testing template rendering")
        
        context = {
            "borrower_name": "Test User",
            "deed": {
                "reference_number": "TEST123",
                "apartment_number": "A1",
                "apartment_address": "Test Address 1",
                "cooperative_name": "Test Cooperative",
                "amount": "1,000,000 SEK",
                "created_date": "2024-01-01"
            },
            "signing_url": "https://example.com/sign/test-token",
            "from_name": settings.EMAILS_FROM_NAME,
            "current_year": 2024
        }
        
        try:
            html_content = render_template("borrower_notification.html", context)
            logger.info(f"Template rendered successfully, length: {len(html_content)}")
            return {"message": "Template rendered successfully", "length": len(html_content)}
        except Exception as e:
            logger.error(f"Template rendering failed: {str(e)}")
            return {"message": f"Template rendering failed: {str(e)}"}
            
    except Exception as e:
        logger.error(f"Error in template test: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Template test failed: {str(e)}"
        )

@router.get(
    "/test-mailgun",
    summary="Test Mailgun API",
    description="Test endpoint to verify Mailgun API configuration."
)
async def test_mailgun_api(
    settings = Depends(get_settings)
):
    """Test Mailgun API configuration."""
    try:
        import httpx
        
        logger.info("Testing Mailgun API configuration")
        logger.info(f"Mailgun Domain: {settings.MAILGUN_DOMAIN}")
        logger.info(f"From Email: {settings.EMAILS_FROM_EMAIL}")
        logger.info(f"API Key length: {len(settings.MAILGUN_API_KEY)}")
        
        mailgun_url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
        
        # Test with a simple email
        data = {
            "from": f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>",
            "to": "test@example.com",
            "subject": "Test Email",
            "text": "This is a test email from the Mortgage Deed System."
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                mailgun_url,
                data=data,
                auth=("api", settings.MAILGUN_API_KEY)
            )
            
            logger.info(f"Mailgun API response status: {response.status_code}")
            logger.info(f"Mailgun API response: {response.text}")
            
            if response.status_code == 200:
                return {"message": "Mailgun API test successful", "status": response.status_code}
            else:
                return {"message": f"Mailgun API test failed", "status": response.status_code, "response": response.text}
                
    except Exception as e:
        logger.error(f"Error in Mailgun test: {str(e)}")
        return {"message": f"Mailgun test failed: {str(e)}"} 

@router.get(
    "/test-specific-email",
    summary="Test specific email sending",
    description="Test endpoint to send email to skyroomdev1@gmail.com"
)
async def test_specific_email(
    settings = Depends(get_settings)
):
    """Test email sending to specific address."""
    try:
        import httpx
        
        logger.info("Testing email sending to skyroomdev1@gmail.com")
        
        mailgun_url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
        
        # Test with the specific email
        data = {
            "from": f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>",
            "to": "skyroomdev1@gmail.com",
            "subject": "Test Email - Mortgage Deed System",
            "text": "This is a test email from the Mortgage Deed System. If you receive this, the email system is working!"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                mailgun_url,
                data=data,
                auth=("api", settings.MAILGUN_API_KEY)
            )
            
            logger.info(f"Mailgun API response status: {response.status_code}")
            logger.info(f"Mailgun API response: {response.text}")
            
            if response.status_code == 200:
                return {"message": "Email sent successfully to skyroomdev1@gmail.com", "status": response.status_code}
            else:
                return {"message": f"Email failed", "status": response.status_code, "response": response.text}
                
    except Exception as e:
        logger.error(f"Error in specific email test: {str(e)}")
        return {"message": f"Specific email test failed: {str(e)}"} 

@router.get(
    "/sign/{token}",
    response_class=HTMLResponse,
    summary="Signing page",
    description="Serves the signing page for borrowers to sign mortgage deeds."
)
async def signing_page(
    token: str,
    supabase: SupabaseClient = Depends(get_supabase)
) -> HTMLResponse:
    """Serve the signing page for a mortgage deed."""
    try:
        print(f"DEBUG: signing_page called with token: {token[:10]}...")
        print(f"DEBUG: Function signature: signing_page(token: str, supabase: SupabaseClient)")
        
        logger.info(f"Loading signing page for token: {token[:10]}...")
        
        # Get signing token
        logger.info("Fetching signing token from database...")
        token_result = await handle_supabase_operation(
            operation_name="fetch signing token for page",
            operation=supabase.table("signing_tokens")
                .select("*")
                .eq("token", token)
                .single()
                .execute(),
            error_msg="Failed to fetch signing token"
        )
        
        logger.info(f"Token result: {token_result.data is not None}")
        
        if not token_result.data:
            logger.info("Token not found, returning invalid token message")
            return HTMLResponse(content="<h1>Invalid Token</h1><p>The signing link is invalid or has expired.</p>")
        
        signing_token = token_result.data
        logger.info(f"Found signing token for deed_id: {signing_token['deed_id']}")
        
        # Check if token is expired
        logger.info("Checking token expiration...")
        expires_at = datetime.fromisoformat(signing_token["expires_at"].replace("Z", "+00:00"))
        current_time = datetime.now().replace(tzinfo=expires_at.tzinfo)
        if expires_at < current_time:
            logger.info("Token expired, returning expired message")
            return HTMLResponse(content="<h1>Expired Token</h1><p>This signing link has expired.</p>")
        
        # Check if token is already used
        logger.info("Checking if token is already used...")
        if signing_token["used_at"]:
            logger.info("Token already used, returning already signed message")
            return HTMLResponse(content="<h1>Already Signed</h1><p>This mortgage deed has already been signed.</p>")
        
        # Get deed information
        logger.info("Fetching deed information...")
        deed_result = await handle_supabase_operation(
            operation_name="fetch deed for signing",
            operation=supabase.table("mortgage_deeds")
                .select("*, borrowers(*), housing_cooperative:housing_cooperatives(*)")
                .eq("id", signing_token["deed_id"])
                .single()
                .execute(),
            error_msg="Failed to fetch deed information"
        )
        
        logger.info(f"Deed result: {deed_result.data is not None}")
        
        if not deed_result.data:
            logger.info("Deed not found, returning deed not found message")
            return HTMLResponse(content="<h1>Deed Not Found</h1><p>The mortgage deed could not be found.</p>")
        
        deed = deed_result.data
        logger.info("Successfully fetched deed information, generating HTML...")
        
        # Create a simple HTML for testing
        html_content = f"""
        <!DOCTYPE html>
        <html lang="sv">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Digital Signering - Pantbrev</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .deed-info {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .sign-button {{
                    background: #28a745;
                    color: white;
                    padding: 15px 30px;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                    margin: 20px 0;
                }}
                .sign-button:hover {{
                    background: #218838;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Digital Signering</h1>
                    <p>Pantbrev väntar på din signering</p>
                </div>
                
                <div class="deed-info">
                    <h3>📋 Pantbrevsinformation</h3>
                    <p><strong>Referensnummer:</strong> {deed.get('credit_number', 'N/A')}</p>
                    <p><strong>Lägenhetsnummer:</strong> {deed.get('apartment_number', 'N/A')}</p>
                    <p><strong>Adress:</strong> {deed.get('apartment_address', 'N/A')}</p>
                    <p><strong>Status:</strong> {deed.get('status', 'N/A')}</p>
                </div>
                
                <div style="text-align: center;">
                    <h3>🔐 Säker Digital Signering</h3>
                    <p>Klicka på knappen nedan för att signera pantbrevet digitalt</p>
                    <button class="sign-button" onclick="signDeed()">
                        📝 Signera Pantbrev Digitalt
                    </button>
                </div>
            </div>
            
            <script>
                async function signDeed() {{
                    const button = document.querySelector('.sign-button');
                    button.disabled = true;
                    button.textContent = '⏳ Signerar...';
                    
                    try {{
                        console.log('Sending signing request...');
                        const response = await fetch('/api/signing/sign', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                            body: JSON.stringify({{
                                token: '{token}'
                            }})
                        }});
                        
                        console.log('Response status:', response.status);
                        const result = await response.json();
                        console.log('Response data:', result);
                        
                        if (response.ok) {{
                            button.textContent = '✅ Signerat!';
                            button.style.background = '#28a745';
                            alert('Pantbrevet har signerats framgångsrikt!');
                        }} else {{
                            throw new Error(result.detail || 'Signering misslyckades');
                        }}
                    }} catch (error) {{
                        console.error('Error during signing:', error);
                        button.disabled = false;
                        button.textContent = '📝 Signera Pantbrev Digitalt';
                        alert('Ett fel uppstod vid signering: ' + error.message);
                    }}
                }}
                
                console.log('Signing page loaded with token:', '{token}');
            </script>
        </body>
        </html>
        """
        
        logger.info("HTML generated successfully, returning response...")
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"DEBUG: Exception in signing_page: {e}")
        logger.error(f"Error serving signing page: {str(e)}")
        return HTMLResponse(content="<h1>Error</h1><p>An error occurred while loading the signing page.</p>") 