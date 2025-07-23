import requests
import json
import certifi

print(certifi.where())
# Choose the appropriate URL for your environment
API_URL = "https://appapi2.test.bankid.com/rp/v6.0/sign"

# Example payload (base64-encoded userVisibleData, Markdown format)
payload = {
    "endUserIp": "192.168.142.180",
    "userVisibleData": "I0V4YW1wbGUKVGhpcyBpcyBhbiAqZXhhbXBsZSogdGV4dA==",
    "userVisibleDataFormat": "simpleMarkdownV1",
    "returnUrl": "https://bankid.example/auth/login_page#nonce=a3618c72-bc71-4002-b3de-509555b175db"
    # Optionally add 'requirement', 'app', or 'web' keys as needed
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(API_URL, data=json.dumps(payload), headers=headers, verify=False)

print(response.status_code, response.text)

if response.status_code == 200:
    order_response = response.json()
    print("OrderRef:", order_response.get("orderRef"))
    print("AutoStartToken:", order_response.get("autoStartToken"))
else:
    print("Error:", response.status_code, response.text)
