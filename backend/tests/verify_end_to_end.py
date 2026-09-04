"""
Live API End-to-End Verification Script
Tests upload, profile generation, and ask query endpoints on running FastAPI backend.
"""

import os
import httpx

BASE_URL = "http://127.0.0.1:8000/api"
SAMPLE_FILE = os.path.join(os.path.dirname(__file__), "..", "sample_data", "sales_dataset.csv")

def run_verification():
    print("--- 1. Testing Health Endpoint ---")
    with httpx.Client() as client:
        res = client.get("http://127.0.0.1:8000/health")
        print(f"Health Response: {res.status_code} -> {res.json()}")
        assert res.status_code == 200

        print("\n--- 2. Testing Dataset Upload Endpoint ---")
        with open(SAMPLE_FILE, "rb") as f:
            files = {"file": ("sales_dataset.csv", f, "text/csv")}
            res = client.post(f"{BASE_URL}/datasets/upload", files=files)
        
        print(f"Upload Response: {res.status_code}")
        assert res.status_code == 201
        meta = res.json()
        dataset_id = meta["dataset_id"]
        print(f"Dataset Registered ID: {dataset_id}")
        print(f"Rows: {meta['row_count']}, Columns: {meta['column_count']}, Missing Pct: {meta['total_missing_percentage']}%")

        print("\n--- 3. Testing Auto-Profile Endpoint ---")
        res = client.get(f"{BASE_URL}/datasets/{dataset_id}/profile")
        print(f"Profile Response: {res.status_code}")
        assert res.status_code == 200
        profile = res.json()
        print(f"Generated Charts Count: {len(profile['charts'])}")
        for ch in profile['charts']:
            print(f" - Chart: {ch['title']} (Type: {ch['chart_type']})")

        print("\n--- 4. Testing NL2SQL /ask Endpoint ---")
        ask_payload = {
            "dataset_id": dataset_id,
            "question": "What is the total sales amount by category?"
        }
        res = client.post(f"{BASE_URL}/ask", json=ask_payload)
        print(f"Ask Endpoint Status: {res.status_code}")
        if res.status_code == 200:
            ask_data = res.json()
            print(f"Generated SQL:\n{ask_data['sql']}")
            print(f"Explanation:\n{ask_data['explanation']}")
            print(f"Returned Row Count: {ask_data['row_count']}")
        else:
            print(f"Ask response details: {res.json()}")

        print("\n--- 5. End-to-End API Checks Completed! ---")

if __name__ == "__main__":
    run_verification()
