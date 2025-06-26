#!/usr/bin/env python3
"""
Comprehensive Analysis Test
Tests both user-focused and overall analysis types
"""

import sys
import os
import time
import requests
import json

def test_comprehensive_analysis():
    """Test both analysis types"""
    base_url = "http://localhost:5000"
    
    print("🔍 Comprehensive Analysis Test")
    print("=" * 60)
    
    # Check server
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not accessible: {response.status_code}")
            return False
        print("✅ Server is running")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return False
    
    # Test data for different scenarios
    test_scenarios = [
        {
            'name': 'User-Focused Analysis',
            'data': {
                'analysis_type': 'user_focus',
                'token': 'test-token',
                'base_url': 'https://stash.arubanetworks.com',
                'workspace': 'TEST',
                'repo_slug': 'test-repo',
                'focus_user': 'Test User',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'group_by': 'month'
            },
            'should_require_user': True
        },
        {
            'name': 'Overall Repository Analysis',
            'data': {
                'analysis_type': 'overall',
                'token': 'test-token',
                'base_url': 'https://stash.arubanetworks.com',
                'workspace': 'TEST',
                'repo_slug': 'test-repo',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'group_by': 'month'
            },
            'should_require_user': False
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n🧪 Testing: {scenario['name']}")
        print("-" * 40)
        
        # Test with missing user for user-focused analysis
        if scenario['should_require_user']:
            test_data = scenario['data'].copy()
            test_data.pop('focus_user', None)  # Remove focus_user
            
            try:
                response = requests.post(f"{base_url}/analyze", data=test_data)
                if "User-focused analysis requires a focus user" in response.text:
                    print("✅ Correctly rejects user-focused analysis without focus_user")
                else:
                    print("❌ Should reject user-focused analysis without focus_user")
            except Exception as e:
                print(f"⚠️  Error testing missing user validation: {e}")
        
        # Test form validation
        try:
            # This will fail authentication but should pass form validation
            response = requests.post(f"{base_url}/analyze", data=scenario['data'])
            
            # We expect either a progress redirect or an error about connection
            if response.status_code in [302, 200]:
                if response.status_code == 302:
                    print("✅ Form validation passed - redirected to progress")
                else:
                    print("✅ Form validation passed - got response")
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Error testing form submission: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Comprehensive Analysis Test Complete")
    print("\nManual testing recommended:")
    print("1. Start server: python bitbucket_loc_analyzer_ui.py")
    print("2. Open http://localhost:5000")
    print("3. Test user-focused analysis with a real user")
    print("4. Test overall analysis without specifying user")
    print("5. Verify tab behavior in results")
    
    return True

if __name__ == "__main__":
    success = test_comprehensive_analysis()
    sys.exit(0 if success else 1)
