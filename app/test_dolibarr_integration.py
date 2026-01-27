#!/usr/bin/env python
"""
Comprehensive test script for Dolibarr API integration
"""
import requests
import json
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

def print_test(title):
    print(f"\n{'='*70}")
    print(f"🧪 {title}")
    print('='*70)

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def make_request(method, endpoint, expected_status=200):
    """Make HTTP request and display results"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n  Request: {method} {endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, timeout=5)
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == expected_status:
            print_success(f"Endpoint responded with {response.status_code}")
            try:
                data = response.json()
                return data
            except:
                return response.text
        else:
            print_error(f"Expected {expected_status}, got {response.status_code}")
            return None
    except requests.exceptions.ConnectionError as e:
        print_error(f"Connection failed: {e}")
        return None
    except Exception as e:
        print_error(f"Request failed: {e}")
        return None

def test_api_health():
    """Test basic API health"""
    print_test("API HEALTH CHECK")
    
    data = make_request("GET", "/")
    if data:
        print(f"  Response: {json.dumps(data, indent=2)}")
        return True
    return False

def test_dolibarr_connection():
    """Test Dolibarr database connection"""
    print_test("DOLIBARR DATABASE CONNECTION")
    
    data = make_request("GET", "/api/v1/dolibarr/test-connection")
    if data:
        print(f"  Response: {json.dumps(data, indent=2)}")
        return True
    return False

def test_dolibarr_products():
    """Test getting products from Dolibarr"""
    print_test("DOLIBARR PRODUCTS LIST")
    
    data = make_request("GET", "/api/v1/dolibarr/products?limit=5")
    if data:
        print(f"  Response (first 300 chars):")
        response_str = json.dumps(data, indent=2, default=str)
        print(f"  {response_str[:300]}...")
        if data.get('count') is not None:
            print_success(f"Found {data['count']} products")
        return True
    return False

def test_dolibarr_companies():
    """Test getting companies from Dolibarr"""
    print_test("DOLIBARR COMPANIES LIST")
    
    data = make_request("GET", "/api/v1/dolibarr/companies?limit=5")
    if data:
        if data.get('count') is not None:
            if data['count'] > 0:
                print_success(f"Found {data['count']} companies")
            else:
                print("  ℹ️  No companies in Dolibarr (this is normal for a fresh install)")
        return True
    return False

def test_dolibarr_orders():
    """Test getting orders from Dolibarr"""
    print_test("DOLIBARR ORDERS LIST")
    
    data = make_request("GET", "/api/v1/dolibarr/orders?limit=5")
    if data:
        if data.get('count') is not None:
            if data['count'] > 0:
                print_success(f"Found {data['count']} orders")
            else:
                print("  ℹ️  No orders in Dolibarr (this is normal for a fresh install)")
        return True
    return False

def test_dolibarr_warehouses():
    """Test getting warehouses from Dolibarr"""
    print_test("DOLIBARR WAREHOUSES")
    
    data = make_request("GET", "/api/v1/dolibarr/warehouses")
    if data:
        print(f"  Response: {json.dumps(data, indent=2, default=str)}")
        if data.get('count') is not None:
            print_success(f"Found {data['count']} warehouses")
        return True
    return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 DOLIBARR API INTEGRATION TEST SUITE")
    print("="*70)
    
    print(f"\nTarget: {BASE_URL}")
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    results = []
    
    # Run all tests
    results.append(("API Health", test_api_health()))
    results.append(("Dolibarr Connection", test_dolibarr_connection()))
    results.append(("Products", test_dolibarr_products()))
    results.append(("Companies", test_dolibarr_companies()))
    results.append(("Orders", test_dolibarr_orders()))
    results.append(("Warehouses", test_dolibarr_warehouses()))
    
    # Summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nResult: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✨ All tests passed! Dolibarr integration is working correctly!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        sys.exit(1)
