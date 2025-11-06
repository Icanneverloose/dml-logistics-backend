"""
Quick test script to verify token authentication is working
Run this after deploying the backend changes
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:5000/api"  # Change to your backend URL
TEST_EMAIL = "tokentest@example.com"
TEST_PASSWORD = "test123456"
TEST_NAME = "Token Test User"

print("=" * 60)
print("Token Authentication Test")
print("=" * 60)

# Test 1: Sign up and get token
print("\n1. Testing Signup with Token...")
signup_response = requests.post(
    f"{BASE_URL}/user/signup",
    json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    },
    headers={"Content-Type": "application/json"}
)

print(f"   Status: {signup_response.status_code}")
signup_data = signup_response.json()
print(f"   Success: {signup_data.get('success')}")

if signup_data.get('token'):
    print(f"   ✅ Token received: {signup_data['token'][:20]}...")
    token = signup_data['token']
else:
    print(f"   ❌ No token in response")
    print(f"   Response: {json.dumps(signup_data, indent=2)}")
    exit(1)

# Test 2: Use token to get profile
print("\n2. Testing Profile Access with Token...")
profile_response = requests.get(
    f"{BASE_URL}/user/profile",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
)

print(f"   Status: {profile_response.status_code}")
profile_data = profile_response.json()
print(f"   Success: {profile_data.get('success')}")

if profile_data.get('success') and profile_data.get('user'):
    print(f"   ✅ Profile retrieved: {profile_data['user']['email']}")
else:
    print(f"   ❌ Failed to get profile")
    print(f"   Response: {json.dumps(profile_data, indent=2)}")

# Test 3: Login and get token
print("\n3. Testing Login with Token...")
login_response = requests.post(
    f"{BASE_URL}/user/login",
    json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    },
    headers={"Content-Type": "application/json"}
)

print(f"   Status: {login_response.status_code}")
login_data = login_response.json()
print(f"   Success: {login_data.get('success')}")

if login_data.get('token'):
    print(f"   ✅ Token received: {login_data['token'][:20]}...")
else:
    print(f"   ❌ No token in response")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
print("\nSummary:")
print("  - Signup returns token: ✅" if signup_data.get('token') else "  - Signup returns token: ❌")
print("  - Login returns token: ✅" if login_data.get('token') else "  - Login returns token: ❌")
print("  - Token auth works: ✅" if profile_data.get('success') else "  - Token auth works: ❌")
print("\n✅ All tests passed! Token authentication is working." if all([
    signup_data.get('token'),
    login_data.get('token'),
    profile_data.get('success')
]) else "\n⚠️  Some tests failed. Check the output above.")

