#!/usr/bin/env python
"""
Simple test for Dolibarr integration
"""
import subprocess
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

print("\n" + "="*70)
print("✨ DOLIBARR DATABASE INTEGRATION TEST")
print("="*70)

time.sleep(2)

endpoints = [
    ("/api/v1/dolibarr/test-connection", "Connection Test"),
    ("/api/v1/dolibarr/products?limit=3", "Products List"),
    ("/api/v1/dolibarr/companies", "Companies List"),
    ("/api/v1/dolibarr/orders", "Orders List"),
    ("/api/v1/dolibarr/warehouses", "Warehouses List"),
]

results = []

for endpoint, name in endpoints:
    print(f"\n🧪 Testing: {name}")
    print(f"   Endpoint: GET {endpoint}")
    
    cmd = f'curl.exe -s "{BASE_URL}{endpoint}"'
    
    try:
        output = subprocess.check_output(cmd, shell=True, text=True, timeout=10)
        data = json.loads(output)
        
        if data.get("status") in ["success", "connected"]:
            print(f"   ✅ SUCCESS - Status: {data.get('status')}")
            if "count" in data:
                print(f"   Count: {data['count']}")
            results.append((name, True))
        else:
            print(f"   ⚠️  Response: {data}")
            results.append((name, False))
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Timeout")
        results.append((name, False))
    except json.JSONDecodeError:
        print(f"   ❌ Invalid JSON response")
        results.append((name, False))
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append((name, False))

print("\n" + "="*70)
print("📋 SUMMARY")
print("="*70)

for name, passed in results:
    status = "✅" if passed else "❌"
    print(f"{status} {name}")

passed_count = sum(1 for _, p in results if p)
print(f"\nResult: {passed_count}/{len(results)} tests passed\n")

if passed_count == len(results):
    print("✨ All tests passed! Dolibarr integration is working!")
    sys.exit(0)
else:
    print(f"⚠️ {len(results) - passed_count} test(s) failed")
    sys.exit(1)
