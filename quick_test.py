#!/usr/bin/env python3
"""
Quick test script to verify the application works.
Run this after starting the API server.
"""
import requests
import sys
import time

API_URL = "http://localhost:8000"

def print_status(message, status="INFO"):
    """Print colored status message."""
    colors = {
        "PASS": "\033[92m",  # Green
        "FAIL": "\033[91m",  # Red
        "INFO": "\033[94m",  # Blue
        "END": "\033[0m"     # Reset
    }
    symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "→"
    color = colors.get(status, colors["INFO"])
    print(f"{color}{symbol} {message}{colors['END']}")

def test_health():
    """Test health endpoint."""
    print_status("Testing health endpoint...", "INFO")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print_status("Health check passed", "PASS")
                return True
        print_status(f"Health check failed: {response.status_code}", "FAIL")
        return False
    except requests.exceptions.ConnectionError:
        print_status("Cannot connect to API server. Is it running?", "FAIL")
        print_status("Start it with: python run_api.py", "INFO")
        return False
    except Exception as e:
        print_status(f"Health check error: {e}", "FAIL")
        return False

def test_api_docs():
    """Test API documentation endpoint."""
    print_status("Testing API documentation...", "INFO")
    try:
        response = requests.get(f"{API_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_status("API docs accessible", "PASS")
            return True
        print_status(f"API docs failed: {response.status_code}", "FAIL")
        return False
    except Exception as e:
        print_status(f"API docs error: {e}", "FAIL")
        return False

def test_cache_endpoints():
    """Test cache management endpoints."""
    print_status("Testing cache endpoints...", "INFO")
    try:
        # Test cache info
        response = requests.get(f"{API_URL}/api/cache/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status(f"Cache info: {data.get('cache_size', 0)} entries", "PASS")
        
        # Test cache clear
        response = requests.delete(f"{API_URL}/api/cache", timeout=5)
        if response.status_code == 200:
            print_status("Cache clear endpoint works", "PASS")
            return True
        return False
    except Exception as e:
        print_status(f"Cache test error: {e}", "FAIL")
        return False

def test_menu_endpoint_quick():
    """Test menu endpoint with minimal request (doesn't actually scrape)."""
    print_status("Testing menu endpoint (validation only)...", "INFO")
    try:
        # Test with invalid threads to check validation
        payload = {"threads": 15}  # Invalid - exceeds max of 10
        response = requests.post(f"{API_URL}/api/menus", json=payload, timeout=600)  # 10 min for scraping
        if response.status_code == 422:  # Validation error expected
            print_status("Request validation works", "PASS")
            return True
        print_status(f"Unexpected response: {response.status_code}", "FAIL")
        return False
    except Exception as e:
        print_status(f"Menu endpoint test error: {e}", "FAIL")
        return False

def main():
    """Run all quick tests."""
    print("\n" + "="*60)
    print("  Purdue Menu Helper - Quick Test Suite")
    print("="*60 + "\n")
    
    print_status("Make sure the API server is running:", "INFO")
    print_status("  python run_api.py", "INFO")
    print()
    
    tests = [
        ("Health Endpoint", test_health),
        ("API Documentation", test_api_docs),
        ("Cache Endpoints", test_cache_endpoints),
        ("Menu Endpoint Validation", test_menu_endpoint_quick),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n[{name}]")
        result = test_func()
        results.append((name, result))
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "="*60)
    print("  Test Results Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print_status(f"{name}: {'PASSED' if result else 'FAILED'}", status)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_status("\nAll quick tests passed! ✓", "PASS")
        print_status("\nTo test actual scraping, use:", "INFO")
        print_status("  curl -X POST http://localhost:8000/api/menus \\", "INFO")
        print_status("    -H 'Content-Type: application/json' \\", "INFO")
        print_status("    -d '{\"meals\": [\"Breakfast\"], \"threads\": 1}'", "INFO")
        return 0
    else:
        print_status("\nSome tests failed. Check the errors above.", "FAIL")
        return 1

if __name__ == "__main__":
    sys.exit(main())

