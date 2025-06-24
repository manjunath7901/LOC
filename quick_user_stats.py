#!/usr/bin/env python3
"""
Quick script to analyze user statistics for a Bitbucket repository
Focused only on displaying lines of code for each user without graphs
Uses a limited number of commits for faster execution
"""

import pandas as pd
import json
import os
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

def main():
    # Configuration
    token = "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V"
    base_url = "https://stash.arubanetworks.com"
    workspace = "GVT"
    repo_slug = "cx-switch-health-read-assist"
    max_commits = 20  # Process only this many commits for a quick test
    
    # Create the analyzer
    analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
    
    # Try to load existing commit data if available
    print(f"Checking for cached commit data...")
    json_file = "cx_commits.json"
    commits = None
    
    if os.path.exists(json_file):
        print(f"Loading commits from {json_file}...")
        with open(json_file, 'r') as f:
            data = json.load(f)
            if 'values' in data:
                commits = data['values'][:max_commits]  # Limit to max_commits
                print(f"Loaded {len(commits)} commits from cache")
    
    if not commits:
        print("No cached commits found. Fetching from API...")
        commits = analyzer.get_commits(workspace, repo_slug)[:max_commits]
        print(f"Fetched {len(commits)} commits from API")
    
    if not commits:
        print("No commits found.")
        return
    
    # Process commit data
    print(f"\nProcessing {len(commits)} commits...")
    
    # Directly track user statistics
    user_data = {}
    
    for i, commit in enumerate(commits):
        # Extract commit metadata
        if analyzer.is_stash:  # Stash/Bitbucket Server format
            commit_hash = commit['id']
            # Get author information for user-level stats
            author_name = commit.get('author', {}).get('displayName', 'Unknown')
            author_email = commit.get('author', {}).get('emailAddress', '')
        else:  # Bitbucket Cloud format
            commit_hash = commit['hash']
            author_info = commit.get('author', {})
            author_name = author_info.get('user', {}).get('display_name', 'Unknown')
            author_email = author_info.get('raw', '').split('<')[-1].strip('>')
        
        # Get stats for this commit
        print(f"Processing commit {i+1}/{len(commits)}: {commit_hash[:8]} by {author_name}")
        stats = analyzer.get_commit_stats(workspace, repo_slug, commit_hash)
        
        # Track user stats
        if author_name not in user_data:
            user_data[author_name] = {
                'name': author_name,
                'email': author_email,
                'commits': 0,
                'additions': 0,
                'deletions': 0
            }
        
        user_data[author_name]['commits'] += 1
        user_data[author_name]['additions'] += stats['additions']
        user_data[author_name]['deletions'] += stats['deletions']
    
    # Process user data
    print("\nGenerating user statistics...")
    user_stats = []
    for name, stats in user_data.items():
        user_stats.append({
            'name': name,
            'email': stats['email'],
            'commits': stats['commits'],
            'additions': stats['additions'],
            'deletions': stats['deletions'],
            'total_changes': stats['additions'] + stats['deletions']
        })
    
    # Create DataFrame and sort by total changes
    if user_stats:
        user_df = pd.DataFrame(user_stats).sort_values('total_changes', ascending=False)
        
        # Export user stats to CSV
        csv_file = f"{workspace}_{repo_slug}_quick_user_stats.csv"
        user_df.to_csv(csv_file, index=False)
        print(f"User statistics exported to {csv_file}")
        
        # Print ALL users by total changes
        print("\nUser lines of code statistics:")
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
    else:
        print("No user data was generated")

if __name__ == '__main__':
    main()
