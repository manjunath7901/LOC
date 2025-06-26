#!/usr/bin/env python3
"""
Check what author data exists in repository
"""

from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

def check_authors():
    analyzer = BitbucketLOCAnalyzer(base_url='https://stash.arubanetworks.com', token='test_token')
    
    try:
        # Get recent commits to see author data
        results = analyzer.analyze_repository(
            'GVT',
            'cx-switch-device-health', 
            start_date='2025-06-20',
            end_date='2025-06-26',
            by_user=True
        )
        
        if results and len(results) >= 2:
            daily_data, user_data = results
            print("Available authors in repository:")
            print("=" * 50)
            for idx, user in user_data.iterrows():
                print(f"Name: {user.get('name', 'N/A')}")
                print(f"Email: {user.get('email', 'N/A')}")
                print("-" * 30)
                
        else:
            print("No user data found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_authors()
