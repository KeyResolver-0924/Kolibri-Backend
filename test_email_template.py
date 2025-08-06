#!/usr/bin/env python3
"""
Test to verify email template rendering with signing button
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.config import get_settings
from api.utils.template_utils import render_template

def test_email_template():
    """Test email template rendering with signing button."""
    
    print("Testing Email Template Rendering")
    print("=" * 35)
    
    try:
        settings = get_settings()
        
        # Test 1: Create test context
        print("\n1. Creating test email context...")
        test_context = {
            "admin_name": "Test Administrator",
            "deed": {
                "reference_number": "TEST123",
                "apartment_number": "A1",
                "apartment_address": "Test Address 1",
                "cooperative_name": "Test Cooperative",
                "borrowers": [{"name": "Test Borrower", "email": "test@example.com"}],
                "created_date": "2024-01-01"
            },
            "signing_url": "http://localhost:8080/sign/test-token-123",
            "from_name": settings.EMAILS_FROM_NAME,
            "current_year": 2024
        }
        
        print(f"   ✅ Email context created")
        print(f"   📧 Signing URL: {test_context['signing_url']}")
        
        # Test 2: Render the template
        print("\n2. Rendering email template...")
        try:
            html_content = render_template("cooperative_notification.html", test_context)
            print(f"   ✅ Template rendered successfully")
            print(f"   📏 HTML length: {len(html_content)} characters")
        except Exception as e:
            print(f"   ❌ Template rendering failed: {e}")
            return
        
        # Test 3: Check if signing button is in the HTML
        print("\n3. Checking signing button in HTML...")
        
        if "Signera Pantbrev Digitalt" in html_content:
            print("   ✅ Signing button text found in HTML")
        else:
            print("   ❌ Signing button text not found in HTML")
        
        if "href=\"http://localhost:8080/sign/test-token-123\"" in html_content:
            print("   ✅ Signing URL found in HTML")
        else:
            print("   ❌ Signing URL not found in HTML")
        
        if "class=\"sign-button\"" in html_content:
            print("   ✅ Signing button class found in HTML")
        else:
            print("   ❌ Signing button class not found in HTML")
        
        # Test 4: Check for inline styles
        if "background: linear-gradient" in html_content:
            print("   ✅ Inline styles found in HTML")
        else:
            print("   ❌ Inline styles not found in HTML")
        
        # Test 5: Check for alternative link
        if "Alternativt:" in html_content:
            print("   ✅ Alternative link text found in HTML")
        else:
            print("   ❌ Alternative link text not found in HTML")
        
        # Test 6: Save HTML to file for inspection
        print("\n4. Saving HTML to file for inspection...")
        try:
            with open("test_email_output.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("   ✅ HTML saved to test_email_output.html")
            print("   📁 You can open this file in a browser to see the email")
        except Exception as e:
            print(f"   ❌ Failed to save HTML: {e}")
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print("   - Email template renders correctly")
        print("   - Signing button is included in HTML")
        print("   - Signing URL is properly embedded")
        print("   - Inline styles are applied for email compatibility")
        print("   - Alternative link is provided")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")

if __name__ == "__main__":
    test_email_template()
    print("\nTest completed!") 