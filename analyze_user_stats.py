#!/usr/bin/env python3
"""
Script to analyze user statistics for the Bitbucket repository
Focused on displaying lines of code for each user without graphs
"""

import pandas as pd
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

def main():
    # Configuration
    token = "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V"
    base_url = "https://stash.arubanetworks.com"
    workspace = "GVT"
    repo_slug = "cx-switch-health-read-assist"
    start_date = "2025-06-01"
    end_date = "2025-06-24"
    group_by = "day"
    
    # Create the analyzer
    analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
    
    # Run the analysis
    print(f"Starting analysis of {workspace}/{repo_slug}...")
    print(f"Date range: {start_date} to {end_date}")
    result = analyzer.analyze_repository(
        workspace, 
        repo_slug, 
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
        by_user=True
    )
    
    # Handle both standard and user-level analysis results
    data, user_df = result
    
    # Export data to CSV
    csv_file = f"{workspace}_{repo_slug}_user_stats.csv"
    if data is not None:
        print("\nCode changes summary:")
        total_additions = data['additions'].sum()
        total_deletions = data['deletions'].sum()
        total_changes = total_additions + total_deletions
        print(f"Total additions: {total_additions} lines")
        print(f"Total deletions: {total_deletions} lines")
        print(f"Total changes: {total_changes} lines (sum of additions and deletions)")
        
        # Export data to CSV
        data.to_csv(f"{workspace}_{repo_slug}_loc_data.csv", index=False)
        print(f"Data exported to {workspace}_{repo_slug}_loc_data.csv")
        
    # Output user statistics if available
    if user_df is not None:
        print("\nUser lines of code statistics:")
        
        # Sort by total changes
        user_df['total_changes'] = user_df['additions'] + user_df['deletions']
        user_df = user_df.sort_values(by='total_changes', ascending=False)
        
        # Export user stats to CSV
        user_df.to_csv(csv_file, index=False)
        print(f"User statistics exported to {csv_file}")
        
        # Print ALL users by total changes
        print("\nAll contributors (sorted by total changes):")
        print("-------------------------------------------")
        print("| {:<30} | {:>10} | {:>10} | {:>10} | {:>10} |".format("Name", "Commits", "Additions", "Deletions", "Total"))
        print("|--------------------------------|------------|------------|------------|------------|")
        for _, user in user_df.iterrows():
            print("| {:<30} | {:>10} | {:>10} | {:>10} | {:>10} |".format(
                user['name'][:30], 
                user['commits'], 
                int(user['additions']), 
                int(user['deletions']), 
                int(user['total_changes'])
            ))
        print("-------------------------------------------")
        print(f"Total users: {len(user_df)}")

if __name__ == '__main__':
    main()
