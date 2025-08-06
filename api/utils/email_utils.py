import httpx
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from api.config import Settings
from api.utils.template_utils import render_template

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Default placeholder logo using system styling colors
DEFAULT_LOGO_URL = "https://placehold.co/300x100/64748b/ffffff?text=Mortgage+Deed+System"

async def send_email(
    recipient_email: str,
    subject: str,
    template_name: str,
    template_context: Dict[str, Any],
    settings: Settings
) -> bool:
    """
    Send an HTML email using templates through Mailgun API.
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject
        template_name: Name of the template file to use
        template_context: Context data for the template
        settings: Application settings
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        logger.info(f"Starting email send process to {recipient_email}")
        logger.info(f"Using template: {template_name}")
        logger.info(f"Mailgun settings - Domain: {settings.MAILGUN_DOMAIN}, From: {settings.EMAILS_FROM_EMAIL}")
        logger.info(f"Template context keys: {list(template_context.keys())}")
        
        # Add common template variables
        context = {
            **template_context,
            'logo_url': getattr(settings, 'COMPANY_LOGO_URL', None),  # Now None is acceptable as fallback
            'current_year': datetime.now().year
        }
        
        logger.info("Rendering email template...")
        # Render the HTML template
        html_content = render_template(template_name, context)
        logger.info("Successfully rendered email template")
        logger.info(f"HTML content length: {len(html_content)} characters")
        
        # Prepare the email data
        data = {
            "from": f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>",
            "to": recipient_email,
            "subject": subject,
            "html": html_content
        }
        logger.info(f"Prepared email data - From: {data['from']}, To: {data['to']}, Subject: {data['subject']}")
        
        mailgun_url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
        logger.info(f"Using Mailgun URL: {mailgun_url}")
        
        async with httpx.AsyncClient() as client:
            logger.info("Making request to Mailgun API...")
            response = await client.post(
                mailgun_url,
                data=data,
                auth=("api", settings.MAILGUN_API_KEY)
            )
            response_text = response.text
            logger.info(f"Mailgun API response status: {response.status_code}")
            logger.info(f"Mailgun API response: {response_text}")
            
            if response.status_code == 200:
                logger.info(f"Email sent successfully to {recipient_email}")
                return True
            else:
                logger.error(f"Failed to send email. Status: {response.status_code}, Error: {response_text}")
                return False
                    
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", exc_info=True)
        return False 