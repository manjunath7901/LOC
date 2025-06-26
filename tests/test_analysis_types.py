#!/usr/bin/env python3
"""
Test the updated UI with different analysis types
"""

import requests
import time
import webbrowser

def test_user_focused_analysis():
    """Test user-focused analysis"""
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Testing User-Focused Analysis")
    print("=" * 50)
    
    user_data = {
        'token': 'test_token',
        'base_url': 'https://stash.arubanetworks.com',
        'workspace': 'GVT',
        'repo_slug': 'cx-switch-device-health',
        'start_date': '2025-06-20',
        'end_date': '2025-06-26',
        'group_by': 'day',
        'focus_user': 'Kallatti',
        'analysis_type': 'user_focus'
    }
    
    try:
        response = requests.post(f"{base_url}/analyze", data=user_data, allow_redirects=False)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location', '')
            analysis_id = redirect_url.split('/progress/')[-1]
            print(f"Analysis ID: {analysis_id}")
            print("✅ User-focused analysis submitted successfully")
            return analysis_id
        else:
            print(f"❌ Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_overall_analysis():
    """Test overall repository analysis"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n🧪 Testing Overall Repository Analysis")
    print("=" * 50)
    
    overall_data = {
        'token': 'test_token',
        'base_url': 'https://stash.arubanetworks.com',
        'workspace': 'GVT',
        'repo_slug': 'cx-switch-device-health',
        'start_date': '2025-06-20',
        'end_date': '2025-06-26',
        'group_by': 'day',
        'analysis_type': 'overall'
        # Note: no focus_user for overall analysis
    }
    
    try:
        response = requests.post(f"{base_url}/analyze", data=overall_data, allow_redirects=False)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location', '')
            analysis_id = redirect_url.split('/progress/')[-1]
            print(f"Analysis ID: {analysis_id}")
            print("✅ Overall analysis submitted successfully")
            return analysis_id
        else:
            print(f"❌ Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def wait_for_completion(analysis_id):
    """Wait for analysis to complete"""
    base_url = "http://127.0.0.1:5000"
    
    print(f"⏳ Waiting for analysis {analysis_id} to complete...")
    
    for i in range(30):  # Wait up to 60 seconds
        try:
            status_response = requests.get(f"{base_url}/status/{analysis_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status', 'Unknown')
                progress = status_data.get('progress', 0)
                
                print(f"Status: {status} ({progress}%)")
                
                if status == 'Complete':
                    print("✅ Analysis completed!")
                    return True
                elif status.startswith('Error'):
                    print(f"❌ Analysis failed: {status}")
                    return False
        except Exception as e:
            print(f"Error checking status: {e}")
        
        time.sleep(2)
    
    print("⏰ Timed out waiting for completion")
    return False

if __name__ == "__main__":
    print("🚀 Testing Updated Analysis Types")
    print("=" * 60)
    
    # Test user-focused analysis
    user_analysis_id = test_user_focused_analysis()
    if user_analysis_id and wait_for_completion(user_analysis_id):
        print(f"🌐 Opening user-focused results: http://127.0.0.1:5000/results/{user_analysis_id}")
        webbrowser.open(f"http://127.0.0.1:5000/results/{user_analysis_id}")
    
    time.sleep(3)
    
    # Test overall analysis
    overall_analysis_id = test_overall_analysis()
    if overall_analysis_id and wait_for_completion(overall_analysis_id):
        print(f"🌐 Opening overall results: http://127.0.0.1:5000/results/{overall_analysis_id}")
        webbrowser.open(f"http://127.0.0.1:5000/results/{overall_analysis_id}")
    
    print("\n✅ Testing complete! Check the opened browser tabs to verify:")
    print("1. User-focused analysis should show 'User Analysis' tab active")
    print("2. Overall analysis should show 'Overall Repository Stats' tab active")
    print("3. Repository information should be clearly displayed")
