#!/usr/bin/env python
"""
Test script para verificar los endpoints de la API WMS
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_root():
    """Test GET /"""
    print("\n" + "="*60)
    print("TEST 1: GET / (Root endpoint)")
    print("="*60)
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"Status Code: {resp.status_code}")
        print(f"Response Body:")
        print(json.dumps(resp.json(), indent=2))
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_health():
    """Test GET /health"""
    print("\n" + "="*60)
    print("TEST 2: GET /health")
    print("="*60)
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status Code: {resp.status_code}")
        print(f"Response Body:")
        print(json.dumps(resp.json(), indent=2))
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_openapi():
    """Test GET /openapi.json"""
    print("\n" + "="*60)
    print("TEST 3: GET /openapi.json")
    print("="*60)
    try:
        resp = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        print(f"Status Code: {resp.status_code}")
        data = resp.json()
        print(f"API Title: {data.get('info', {}).get('title')}")
        print(f"API Version: {data.get('info', {}).get('version')}")
        print(f"Number of Paths: {len(data.get('paths', {}))}")
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_docs():
    """Test GET /docs"""
    print("\n" + "="*60)
    print("TEST 4: GET /docs (Swagger UI)")
    print("="*60)
    try:
        resp = requests.get(f"{BASE_URL}/docs", timeout=5)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print("✓ Swagger UI is accessible")
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    print("\n🚀 Starting API Verification Tests")
    print(f"   Target: {BASE_URL}")
    
    results = []
    time.sleep(1)  # Give server time to fully start
    
    results.append(("GET /", test_root()))
    results.append(("GET /health", test_health()))
    results.append(("GET /openapi.json", test_openapi()))
    results.append(("GET /docs", test_docs()))
    
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\nResult: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("✨ All verification tests passed successfully!")
    else:
        print(f"⚠️  {total_count - passed_count} test(s) failed")
