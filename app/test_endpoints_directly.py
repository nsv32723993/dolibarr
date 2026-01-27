#!/usr/bin/env python
"""
Test Dolibarr endpoints directly using HTTP client
"""
import sys
import time

print("Waiting for server to start...")
time.sleep(3)

print("\nAttempting to import FastAPI app...")
try:
    from fastapi.testclient import TestClient
    from main import app
    print("✓ App imported successfully")
except Exception as e:
    print(f"✗ Failed to import app: {e}")
    sys.exit(1)

print("\nCreating test client...")
try:
    client = TestClient(app)
    print("✓ Test client created")
except Exception as e:
    print(f"✗ Failed to create client: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("Testing Dolibarr Endpoints")
print("="*70)

# Test 1: Connection
print("\n[1] Testing /api/v1/dolibarr/test-connection")
try:
    response = client.get("/api/v1/dolibarr/test-connection")
    print(f"    Status: {response.status_code}")
    print(f"    Response: {response.json()}")
    if response.status_code == 200:
        print("    ✅ PASS")
    else:
        print("    ❌ FAIL")
except Exception as e:
    print(f"    ❌ Error: {e}")

# Test 2: Info
print("\n[2] Testing /api/v1/dolibarr/info")
try:
    response = client.get("/api/v1/dolibarr/info")
    print(f"    Status: {response.status_code}")
    data = response.json()
    print(f"    Response: {data}")
    if response.status_code == 200 and data.get("status") == "success":
        print("    ✅ PASS")
        print(f"    Data: {data.get('data')}")
    else:
        print("    ❌ FAIL")
except Exception as e:
    print(f"    ❌ Error: {e}")

# Test 3: Root
print("\n[3] Testing GET /")
try:
    response = client.get("/")
    print(f"    Status: {response.status_code}")
    print(f"    Response: {response.json()}")
    if response.status_code == 200:
        print("    ✅ PASS")
    else:
        print("    ❌ FAIL")
except Exception as e:
    print(f"    ❌ Error: {e}")

print("\n" + "="*70)
print("✨ Test complete\n")
