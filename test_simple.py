#!/usr/bin/env python3
"""
Simple test for signing functionality
"""

import asyncio
import httpx

async def test_simple():
    """Simple test for signing functionality."""
    
    print("Testing Signing Functionality")
    print("=" * 30)
    
    # Test the signing page endpoint
    print("\nTesting signing page endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8080/api/signing/sign/test-token")
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', '')}")
            
            if response.status_code == 200:
                print("✅ Signing page works")
                html = response.text
                if "Signera Pantbrev Digitalt" in html:
                    print("✅ Contains signing button")
                else:
                    print("❌ Missing signing button")
            else:
                print(f"❌ Signing page failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple()) 