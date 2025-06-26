#!/usr/bin/env python3
"""
Test specific analysis result to see error details
"""

import requests

def test_specific_result():
    base_url = "http://127.0.0.1:5000"
    analysis_id = "GVT_user_1750934184_8788"  # From the last successful test
    
    try:
        response = requests.get(f"{base_url}/results/{analysis_id}")
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_specific_result()
