#!/usr/bin/env python3
"""
Test script to verify signing page functionality
"""

import asyncio
import httpx
import json

async def test_signing_page():
    """Test the signing page functionality."""
    
    # Test URL
    base_url = "http://localhost:8080"
    
    # Test 1: Check if the redirect route works
    print("Testing redirect route...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/sign/test-token")
            print(f"Redirect response status: {response.status_code}")
            print(f"Redirect response headers: {response.headers}")
            if response.status_code == 307:  # Temporary redirect
                print("✅ Redirect route working correctly")
            else:
                print(f"❌ Unexpected redirect response: {response.status_code}")
        except Exception as e:
            print(f"❌ Error testing redirect: {e}")
    
    # Test 2: Check if the signing page endpoint works
    print("\nTesting signing page endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/api/signing/sign/test-token")
            print(f"Signing page response status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Signing page endpoint working")
                # Check if it returns HTML
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    print("✅ Returns HTML content")
                else:
                    print(f"❌ Unexpected content type: {content_type}")
            else:
                print(f"❌ Signing page failed: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Error testing signing page: {e}")
    
    # Test 3: Check if the signing API endpoint works
    print("\nTesting signing API endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/api/signing/sign",
                json={"token": "test-token"}
            )
            print(f"Signing API response status: {response.status_code}")
            if response.status_code == 404:
                print("✅ API correctly returns 404 for invalid token")
            else:
                print(f"❌ Unexpected API response: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Error testing signing API: {e}")

if __name__ == "__main__":
    print("Testing Signing Page Functionality")
    print("=" * 40)
    asyncio.run(test_signing_page())
    print("\nTest completed!") 