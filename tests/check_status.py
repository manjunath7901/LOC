#!/usr/bin/env python3
"""
Check analysis status
"""

import requests
import time

def check_analysis_status():
    base_url = "http://127.0.0.1:5000"
    analysis_id = "GVT_user_1750936613_8732"  # From the last test
    
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/status/{analysis_id}")
            if response.status_code == 200:
                status_data = response.json()
                print(f"Status: {status_data.get('status', 'Unknown')}")
                print(f"Progress: {status_data.get('progress', 0)}%")
                if 'error' in status_data.get('status', '').lower():
                    break
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    check_analysis_status()
