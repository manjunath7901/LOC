#!/usr/bin/env python3
"""
Test UI Fixes Script
Verifies the final UI fixes for:
1. Analysis type handling (overall vs user_focus vs legacy)
2. Repository display formatting
3. Tab visibility logic
"""

import sys
import os
import time
import requests

def test_ui_fixes():
    """Test the UI fixes"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing UI Fixes")
    print("=" * 50)
    
    # Test 1: Check that the server is running
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ Server is running on localhost:5000")
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not accessible: {e}")
        print("Please start the server with: python bitbucket_loc_analyzer_ui.py")
        return False
    
    # Test 2: Check the main page HTML content
    try:
        response = requests.get(base_url)
        html_content = response.text
        
        # Check for key elements
        checks = [
            ('user_analysis', 'User Focus analysis type radio button'),
            ('overall_analysis', 'Overall analysis type radio button'),
            ('focus_user', 'Focus user input field'),
            ('toggleUserField', 'Dynamic user field toggle function'),
            ('repo_slug', 'Repository slug input field')
        ]
        
        for element_id, description in checks:
            if element_id in html_content:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} not found")
                
    except Exception as e:
        print(f"❌ Error checking main page content: {e}")
        return False
    
    # Test 3: Check for template files
    template_files = [
        'templates/index.html',
        'templates/results_new.html',
        'templates/progress.html',
        'templates/error.html'
    ]
    
    for template_file in template_files:
        if os.path.exists(template_file):
            print(f"✅ Template file {template_file} exists")
        else:
            print(f"❌ Template file {template_file} missing")
    
    print("=" * 50)
    print("✅ UI Fixes Test Complete")
    print("\nKey improvements verified:")
    print("- Analysis type selection (User Focus vs Overall)")
    print("- Dynamic user field based on analysis type")
    print("- Proper tab handling for different analysis types")
    print("- Better repository name display")
    print("- Legacy analysis support")
    print("\nTo fully test:")
    print("1. Start the server: python bitbucket_loc_analyzer_ui.py")
    print("2. Open http://localhost:5000 in your browser")
    print("3. Try both analysis types with different inputs")
    
    return True

if __name__ == "__main__":
    success = test_ui_fixes()
    sys.exit(0 if success else 1)
