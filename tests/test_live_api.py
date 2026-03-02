"""
Live smoke test for the deployed PageIndex API on Azure Container Apps.

Usage:
    API_TOKEN=<your-token> python3 tests/test_live_api.py

    Optionally override the API URL:
    API_URL=https://your-custom-url API_TOKEN=<your-token> python3 tests/test_live_api.py
"""

import os
import sys
import json
import requests

API_URL = os.getenv("API_URL", "").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN")
PDF_PATH = os.path.join(os.path.dirname(__file__), "pdfs", "earthmover.pdf")

def main():
    if not API_URL:
        print("ERROR: API_URL environment variable is not set.")
        print("Usage: API_URL=https://your-app-url API_TOKEN=<your-token> python3 tests/test_live_api.py")
        sys.exit(1)

    if not API_TOKEN:
        print("ERROR: API_TOKEN environment variable is not set.")
        print("Usage: API_TOKEN=<your-token> python3 tests/test_live_api.py")
        sys.exit(1)

    if not os.path.exists(PDF_PATH):
        print(f"ERROR: Test PDF not found at {PDF_PATH}")
        sys.exit(1)

    endpoint = f"{API_URL}/index-pdf"

    # --- Test 1: Reject missing API key ---
    print("=" * 60)
    print("Test 1: Missing API Key → expect 401")
    resp = requests.post(endpoint)
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print("  ✅ PASSED\n")

    # --- Test 2: Reject wrong API key ---
    print("Test 2: Wrong API Key → expect 401")
    resp = requests.post(endpoint, headers={"X-API-Key": "wrong-token-12345"})
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print("  ✅ PASSED\n")

    # --- Test 3: Reject non-PDF file ---
    print("Test 3: Non-PDF file → expect 400")
    resp = requests.post(
        endpoint,
        headers={"X-API-Key": API_TOKEN},
        files={"file": ("readme.txt", b"hello world", "text/plain")},
    )
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print("  ✅ PASSED\n")

    # --- Test 4: Valid PDF upload ---
    print("Test 4: Valid PDF upload → expect 200 with JSON structure")
    with open(PDF_PATH, "rb") as f:
        resp = requests.post(
            endpoint,
            headers={"X-API-Key": API_TOKEN},
            files={"file": ("earthmover.pdf", f, "application/pdf")},
            timeout=300,  # PageIndex processing can take a while
        )
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    result = resp.json()
    print(f"  Response type: {type(result).__name__}")
    print(f"  Preview (first 500 chars):")
    print(f"  {json.dumps(result, indent=2)[:500]}")
    print("  ✅ PASSED\n")

    print("=" * 60)
    print("🎉 All live API tests passed!")

if __name__ == "__main__":
    main()
