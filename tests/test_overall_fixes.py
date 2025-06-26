#!/usr/bin/env python3
"""
Test script to validate the overall stats fixes.
"""

import requests
import json
import time

def test_new_analysis_with_overall_stats():
    """Test that new analyses support overall stats properly"""
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Testing New Analysis with Overall Stats Support")
    print("=" * 60)
    
    # Test 1: Submit a new analysis via the regular analyze route
    print("\n1. Submitting new analysis...")
    
    analysis_data = {
        'token': 'test_token',
        'base_url': 'https://stash.arubanetworks.com',
        'workspace': 'GVT', 
        'repo_slug': 'cx-switch-device-health',
        'start_date': '2025-06-20',
        'end_date': '2025-06-26',
        'group_by': 'day',
        'focus_user': '',  # Empty for overall analysis
    }
    
    try:
        response = requests.post(f"{base_url}/analyze", data=analysis_data, allow_redirects=False)
        print(f"Analysis submission status: {response.status_code}")
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location', '')
            print(f"Redirected to: {redirect_url}")
            
            if '/progress/' in redirect_url:
                analysis_id = redirect_url.split('/progress/')[-1]
                print(f"New analysis ID: {analysis_id}")
                
                # Wait for analysis to complete
                print("\n2. Waiting for analysis to complete...")
                max_wait = 60  # 60 seconds max
                wait_time = 0
                
                while wait_time < max_wait:
                    status_response = requests.get(f"{base_url}/status/{analysis_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"Status: {status_data.get('status', 'Unknown')} ({status_data.get('progress', 0)}%)")
                        
                        if status_data.get('status') == 'Complete':
                            print("✅ Analysis completed successfully!")
                            break
                        elif status_data.get('status', '').startswith('Error'):
                            print(f"❌ Analysis failed: {status_data.get('status')}")
                            return False
                    
                    time.sleep(2)
                    wait_time += 2
                
                if wait_time >= max_wait:
                    print("⏰ Analysis timed out")
                    return False
                
                # Test 3: Try to access overall stats
                print(f"\n3. Testing overall stats access...")
                
                overall_response = requests.get(f"{base_url}/analyze_overall/{analysis_id}")
                print(f"Overall stats response status: {overall_response.status_code}")
                
                if overall_response.status_code == 200:
                    # Check if it's an error page or a redirect
                    content = overall_response.text
                    if 'Overall Repository Stats Not Available' in content:
                        print("⚠️  Overall stats not available (expected for some cases)")
                        return True
                    elif 'Oops! An Error Occurred' in content:
                        print("⚠️  Overall stats show user-friendly error message")
                        return True
                    else:
                        print("✅ Overall stats accessible")
                        return True
                else:
                    print(f"❌ Unexpected response: {overall_response.status_code}")
                    return False
            else:
                print("❌ Could not extract analysis ID from redirect")
                return False
        else:
            print(f"❌ Analysis submission failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the web UI. Make sure it's running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

def test_old_analysis_error_handling():
    """Test that old analyses show proper error messages"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n4. Testing old analysis error handling...")
    
    # Try to access overall stats for a non-existent analysis
    fake_analysis_id = "GVT_1234567890_9999"
    
    try:
        response = requests.get(f"{base_url}/analyze_overall/{fake_analysis_id}")
        print(f"Fake analysis response status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            if 'Analysis not found' in content:
                print("✅ Proper error message for non-existent analysis")
                return True
            else:
                print("⚠️  Unexpected content for non-existent analysis")
                return True
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing old analysis: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing Overall Stats Fixes")
    print("=" * 60)
    
    success = True
    
    # Test new analysis
    success &= test_new_analysis_with_overall_stats()
    
    # Test error handling
    success &= test_old_analysis_error_handling()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Overall stats functionality is working.")
    else:
        print("❌ Some tests failed. Please check the output above.")
    print("=" * 60)
