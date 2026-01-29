import requests
import time
import sys

print("[*] Waiting for server...")
time.sleep(2)

try:
    print("[*] Testing GET /...")
    r = requests.get('http://127.0.0.1:8001/', timeout=5)
    print(f"✓ Status: {r.status_code}")
    print(f"✓ Response: {r.json()}")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

try:
    print("\n[*] Testing GET /health...")
    r = requests.get('http://127.0.0.1:8001/health', timeout=5)
    print(f"✓ Status: {r.status_code}")
    print(f"✓ Response: {r.json()}")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\n✅ All tests passed!")
