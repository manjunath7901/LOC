#!/usr/bin/env python3
"""
Test User-Specific Analysis
"""

import requests
import time
import json

def test_user_analysis():
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Testing User-Specific Analysis")
    print("=" * 50)
    
    # Test with a real user that should exist in the repository
    analysis_data = {
        'token': 'test_token',
        'base_url': 'https://stash.arubanetworks.com',
        'workspace': 'GVT', 
        'repo_slug': 'cx-switch-device-health',
        'start_date': '2025-06-12',  # Wider date range for better chance of finding data
        'end_date': '2025-06-26',
        'group_by': 'day',
        'analysis_type': 'user_focus',
        'focus_user': 'sivakumar.murugan@hpe.com',  # This should match the email in the commit
    }
    
    try:
        # Submit the analysis
        response = requests.post(f"{base_url}/analyze", data=analysis_data, allow_redirects=False)
        
        if response.status_code == 302:
            # Extract analysis ID from redirect location
            location = response.headers.get('Location', '')
            analysis_id = location.split('/')[-1]
            print(f"✅ Analysis started with ID: {analysis_id}")
            
            # Monitor progress
            print("📊 Monitoring analysis progress...")
            for i in range(30):  # Wait up to 30 seconds
                status_response = requests.get(f"{base_url}/status/{analysis_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"Progress: {status_data.get('progress', 0)}% - {status_data.get('status', 'Unknown')}")
                    
                    if status_data.get('status') == 'Complete':
                        print("✅ Analysis completed!")
                        
                        # Check results
                        results_response = requests.get(f"{base_url}/results/{analysis_id}")
                        print(f"Results response status: {results_response.status_code}")
                        if results_response.status_code == 200:
                            content = results_response.text
                            print(f"Results content contains: No data found: {'No data found' in content}")
                            print(f"Results content contains: Analysis Results: {'Analysis Results' in content}")
                            print(f"Results content contains: User Analysis: {'User Analysis' in content}")
                            print(f"Results content contains: Error: {'Error' in content}")
                            print(f"First 500 chars of results: {content[:500]}")
                            
                            if "Error" in content and "Error displaying results" in content:
                                print("❌ Error in results template rendering")
                                return False
                            elif "No data found" in content:
                                print("❌ Analysis completed but no data found - user filtering issue")
                                return False
                            elif "Analysis Results" in content or "User Analysis" in content:
                                print("✅ Analysis completed with data - user filtering working!")
                                return True
                            else:
                                print("⚠️  Analysis completed but got error page instead of results")
                                return False
                        else:
                            print(f"❌ Could not fetch results: {results_response.status_code}")
                            return False
                        break
                    elif status_data.get('status') == 'error':
                        print(f"❌ Analysis failed: {status_data.get('error', 'Unknown error')}")
                        return False
                        
                time.sleep(1)
            else:
                print("⏰ Analysis timed out")
                return False
                
        else:
            print(f"❌ Failed to start analysis: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_user_analysis()
    if success:
        print("\n🎉 User-specific analysis is working correctly!")
    else:
        print("\n💥 User-specific analysis needs more debugging")
