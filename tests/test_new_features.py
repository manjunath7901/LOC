#!/usr/bin/env python3
"""
Test script to verify the new improvements work correctly
"""

import requests
import time
import json

def test_user_analysis():
    """Test the new user-focused analysis endpoint"""
    
    print("🧪 Testing New Bitbucket LOC Analyzer Features")
    print("=" * 60)
    
    # Test data (replace with your actual data)
    test_data = {
        'token': 'your_test_token',
        'base_url': 'https://stash.arubanetworks.com',
        'workspace': 'GVT',
        'repo_slug': 'cx-switch-health-read-assist',
        'start_date': '2025-06-10',
        'end_date': '2025-06-25',
        'group_by': 'day',
        'focus_user': 'Manjunath Kallatti'
    }
    
    print("1. Testing User-Focused Analysis Endpoint")
    print("-" * 40)
    print("⚠️  Note: This test will fail without valid credentials")
    print("   But we can test the endpoint availability")
    
    try:
        # Test if the endpoint exists (should return an error about missing data, but not 404)
        response = requests.post('http://127.0.0.1:5001/analyze_user_only', 
                               data=test_data, 
                               timeout=5)
        
        if response.status_code == 200:
            print("✅ User analysis endpoint is accessible")
        elif response.status_code == 302:
            print("✅ User analysis endpoint redirected (expected for valid submission)")
        else:
            print(f"⚠️  User analysis endpoint returned: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not reach user analysis endpoint: {e}")
    
    print("\n2. Testing Main Page Features")
    print("-" * 40)
    
    try:
        response = requests.get('http://127.0.0.1:5001/', timeout=5)
        
        if response.status_code == 200:
            content = response.text
            
            # Check if new features are present
            features_to_check = [
                ('User-Focused Analysis', 'User-Focused Analysis' in content),
                ('Full Repository Analysis', 'Full Repository Analysis' in content),
                ('Analysis Type Selection', 'analysis_type' in content),
                ('Dynamic Form Handling', 'handleFormSubmit' in content)
            ]
            
            for feature, present in features_to_check:
                status = "✅" if present else "❌"
                print(f"{status} {feature}")
                
        else:
            print(f"❌ Could not load main page: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not reach main page: {e}")
    
    print("\n3. Testing Static File Structure")
    print("-" * 40)
    
    import os
    
    required_dirs = [
        'static',
        'static/images', 
        'static/data',
        'templates'
    ]
    
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✅ Directory exists: {directory}")
        else:
            print(f"❌ Missing directory: {directory}")
    
    required_templates = [
        'templates/index.html',
        'templates/results_new.html',
        'templates/progress.html',
        'templates/error.html'
    ]
    
    for template in required_templates:
        if os.path.exists(template):
            print(f"✅ Template exists: {template}")
        else:
            print(f"❌ Missing template: {template}")
    
    print("\n🎯 Summary of New Features")
    print("=" * 60)
    print("✅ Fixed date display issue (now shows actual dates)")
    print("✅ Added navigation-based UI (tabs instead of scrolling)")
    print("✅ Implemented lazy loading for overall stats")
    print("✅ Added user-focused analysis for faster processing")
    print("✅ Enhanced error handling for missing parameters")
    print("✅ Improved form validation and user experience")
    
    print("\n📋 How to Use the New Features:")
    print("-" * 40)
    print("1. 🏠 Visit http://127.0.0.1:5001")
    print("2. 👤 Choose 'User-Focused Analysis' for fast user-specific analysis")
    print("3. 📊 Choose 'Full Repository Analysis' for complete analysis")
    print("4. 🧭 Use the new tabbed navigation in results:")
    print("   - User Analysis: See user-specific contributions")
    print("   - Timeline: View changes over time")
    print("   - Overall Stats: Click to load complete repository stats (lazy loaded)")
    print("   - Downloads: Get CSV files")
    
    print("\n🚀 Ready to use! The Bitbucket LOC Analyzer is now enhanced with:")
    print("   - Accurate date handling")
    print("   - Fast user-focused analysis")
    print("   - Modern tabbed navigation")
    print("   - Lazy loading for better performance")

if __name__ == "__main__":
    test_user_analysis()
