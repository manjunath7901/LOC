#!/usr/bin/env python3
"""
Quick verification script to ensure overall stats are working correctly.
Run this after starting the web UI to verify functionality.
"""

import requests
import webbrowser
import time

def open_ui_and_test():
    """Open the UI and provide testing instructions"""
    base_url = "http://127.0.0.1:5000"
    
    print("🚀 Overall Stats Functionality Verification")
    print("=" * 50)
    
    # Test if UI is running
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            print("✅ Web UI is running successfully!")
            print(f"📱 Opening browser to: {base_url}")
            
            # Open browser
            webbrowser.open(base_url)
            
            print("\n📋 Testing Instructions:")
            print("1. Fill in the form with your repository details")
            print("2. Leave 'Focus User' EMPTY for overall stats")
            print("3. Submit the analysis")
            print("4. Wait for completion")
            print("5. Click 'Overall Repository Stats' tab")
            print("6. Verify data loads correctly")
            
            print("\n🔍 What to Look For:")
            print("- User Analysis tab: Shows filtered user data")
            print("- Timeline tab: Shows time-based charts")
            print("- Overall Repository Stats tab: Shows ALL contributors")
            print("- Downloads tab: Provides CSV files")
            
            print("\n⚠️  Troubleshooting:")
            print("- If 'Overall Repository Stats' shows error:")
            print("  → Start a new analysis (older analyses don't support this)")
            print("- If no data appears:")
            print("  → Check your token and repository access")
            print("- If user filtering doesn't work:")
            print("  → Try different name variations")
            
            return True
        else:
            print(f"❌ UI not responding (status: {response.status_code})")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the web UI")
        print("💡 Make sure the UI is running with:")
        print("   python bitbucket_loc_analyzer_ui.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = open_ui_and_test()
    
    if success:
        print("\n✅ Ready to test overall stats functionality!")
    else:
        print("\n❌ Please start the web UI first and try again.")
