#!/usr/bin/env python3
"""
Test the improved analyzer functionality
"""

import requests
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_improved_ui_submission():
    """Test the improved UI form submission"""
    base_url = "http://127.0.0.1:5000"
    
    analysis_data = {
        'token': 'test_token',
        'base_url': 'https://stash.arubanetworks.com',
        'workspace': 'GVT', 
        'repo_slug': 'cx-switch-device-health, cx-switch-health-read-assist',  # Multiple repos
        'start_date': '2025-06-20',
        'end_date': '2025-06-26',
        'group_by': 'day',
        'analysis_type': 'user_focus',
        'focus_user': 'manjunath.kallatti@hpe.com',
    }
    
    try:
        response = requests.post(f"{base_url}/analyze", data=analysis_data, allow_redirects=False)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response content (first 500 chars): {response.text[:500]}")
        
        if response.status_code == 302:
            print("✅ Redirect working correctly")
            print(f"Redirect location: {response.headers.get('Location', 'Not found')}")
        elif response.status_code == 200:
            print("❌ Getting 200 instead of redirect - checking for errors...")
            if 'error' in response.text.lower():
                print("Found error in response")
            else:
                print("No obvious error - might be a form issue")
                
    except Exception as e:
        print(f"Error: {e}")

def test_direct_analyzer():
    """Test the improved analyzer directly"""
    try:
        from improved_bitbucket_analyzer import ImprovedBitbucketAnalyzer
        
        print("✅ Import successful")
        
        # Test with mock data
        token = "test_token"
        base_url = "https://stash.arubanetworks.com"
        workspace = "GVT"
        
        analyzer = ImprovedBitbucketAnalyzer(token, base_url, workspace)
        print("✅ Analyzer created successfully")
        
        # Test repository list
        repos = ["cx-switch-device-health", "cx-switch-health-read-assist"]
        print(f"✅ Ready to analyze {len(repos)} repositories")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Improved Bitbucket LOC Analyzer")
    print("=" * 50)
    
    print("\n1. Testing direct analyzer import and creation:")
    test_direct_analyzer()
    
    print("\n2. Testing UI form submission:")
    test_improved_ui_submission()
