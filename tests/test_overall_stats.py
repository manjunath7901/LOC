#!/usr/bin/env python3
"""
Test script for overall repository stats functionality.
This script will test the issues mentioned with overall stats.
"""

import requests
import json
import time

def test_overall_stats():
    """Test the overall repository stats functionality"""
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Testing Overall Repository Stats Functionality")
    print("=" * 60)
    
    # Test 1: Submit analysis with user focus first
    print("\n1. Testing user-focused analysis submission...")
    
    user_data = {
        'token': 'test_token',
        'base_url': 'https://stash.arubanetworks.com',
        'workspace': 'GVT',
        'repo_slug': 'cx-switch-health-read-assist',  # Single repo
        'start_date': '2025-01-01',
        'end_date': '2025-01-31',
        'group_by': 'day',
        'focus_user': 'kallatti',  # Specific user
        'analysis_type': 'user_focus'
    }
    
    try:
        response = requests.post(f"{base_url}/analyze_user_only", data=user_data)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 302:  # Redirect to progress
            redirect_url = response.headers.get('Location', '')
            print(f"Redirected to: {redirect_url}")
            
            # Extract analysis ID from redirect URL
            if '/progress/' in redirect_url:
                analysis_id = redirect_url.split('/progress/')[-1]
                print(f"Analysis ID: {analysis_id}")
                
                # Test 2: Try to access overall stats for this analysis
                print(f"\n2. Testing overall stats access for analysis: {analysis_id}")
                
                overall_response = requests.get(f"{base_url}/analyze_overall/{analysis_id}")
                print(f"Overall stats response status: {overall_response.status_code}")
                
                if overall_response.status_code == 200:
                    print("✅ Overall stats route accessible")
                elif overall_response.status_code == 500:
                    print("❌ Internal server error in overall stats")
                    print(f"Response content: {overall_response.text[:200]}...")
                else:
                    print(f"❌ Unexpected response: {overall_response.status_code}")
                    print(f"Response content: {overall_response.text[:200]}...")
                    
                # Test 3: Submit overall analysis (without user focus)
                print(f"\n3. Testing overall analysis submission (no user focus)...")
                
                overall_data = {
                    'token': 'test_token',
                    'base_url': 'https://stash.arubanetworks.com',
                    'workspace': 'GVT',
                    'repo_slug': 'cx-switch-health-read-assist',
                    'start_date': '2025-01-01',
                    'end_date': '2025-01-31',
                    'group_by': 'day',
                    'focus_user': '',  # Empty user for overall stats
                    'analysis_type': 'overall'
                }
                
                overall_submit_response = requests.post(f"{base_url}/analyze", data=overall_data)
                print(f"Overall submission response status: {overall_submit_response.status_code}")
                
                if overall_submit_response.status_code == 302:
                    overall_redirect_url = overall_submit_response.headers.get('Location', '')
                    print(f"Overall analysis redirected to: {overall_redirect_url}")
                    print("✅ Overall analysis submission successful")
                else:
                    print(f"❌ Overall analysis submission failed: {overall_submit_response.status_code}")
                    print(f"Response content: {overall_submit_response.text[:200]}...")
                    
            else:
                print("❌ Could not extract analysis ID from redirect")
        else:
            print(f"❌ User analysis submission failed: {response.status_code}")
            print(f"Response content: {response.text[:200]}...")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the web UI. Make sure it's running on http://127.0.0.1:5000")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed. Check the results above.")

if __name__ == "__main__":
    test_overall_stats()
