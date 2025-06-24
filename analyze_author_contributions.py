#!/usr/bin/env python3
"""
Script to analyze Bitbucket contributions by author rather than committer
"""
import pandas as pd
import json
import os
import sys
import subprocess
import datetime
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

def main():
    # Get parameters from environment or command line
    token = os.environ.get('BITBUCKET_TOKEN', "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V")
    base_url = os.environ.get('BITBUCKET_BASE_URL', "https://stash.arubanetworks.com")
    workspace = "GVT"
    repo_slug = "cx-switch-health-read-assist"
    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Create the analyzer
    analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
    
    # Get all commits for the specified date range
    print(f"Fetching commits from {start_date} to {end_date}...")
    commits = analyzer.get_commits(workspace, repo_slug, start_date, end_date)
    
    if not commits:
        print("No commits found.")
        return
    
    # Track contributions by author (not committer)
    print(f"\nAnalyzing {len(commits)} commits...")
    author_data = {}
    
    for i, commit in enumerate(commits):
        # Extract commit metadata - focus on author information
        if analyzer.is_stash:  # Stash/Bitbucket Server format
            commit_hash = commit['id']
            # Get author information (the person who created the code)
            author_name = commit.get('author', {}).get('displayName', 'Unknown')
            author_email = commit.get('author', {}).get('emailAddress', '')
            
            # Additional debug info to understand the relationship
            committer_name = commit.get('committer', {}).get('displayName', 'Same as Author')
            message = commit.get('message', '').split('\n')[0][:50]  # First line of commit message
            
            print(f"Commit {i+1}/{len(commits)}: {commit_hash[:8]}")
            print(f"  Author: {author_name}")
            print(f"  Committer: {committer_name}")
            print(f"  Message: {message}")
        else:  # Bitbucket Cloud format
            commit_hash = commit['hash']
            author_info = commit.get('author', {})
            author_name = author_info.get('user', {}).get('display_name', 'Unknown')
            author_email = author_info.get('raw', '').split('<')[-1].strip('>')
        
        # Get stats for this commit, counting it toward the AUTHOR, not committer
        stats = analyzer.get_commit_stats(workspace, repo_slug, commit_hash)
        
        # Initialize author entry if not present
        if author_name not in author_data:
            author_data[author_name] = {
                'name': author_name,
                'email': author_email,
                'commits': 0,
                'additions': 0,
                'deletions': 0,
                'commit_hashes': []  # Store commit hashes for reference
            }
        
        # Update stats
        author_data[author_name]['commits'] += 1
        author_data[author_name]['additions'] += stats['additions']
        author_data[author_name]['deletions'] += stats['deletions']
        author_data[author_name]['commit_hashes'].append(commit_hash[:8])
    
    # Process author data
    print("\nGenerating author statistics...")
    author_stats = []
    for name, stats in author_data.items():
        author_stats.append({
            'name': name,
            'email': stats['email'],
            'commits': stats['commits'],
            'additions': stats['additions'],
            'deletions': stats['deletions'],
            'total_changes': stats['additions'] + stats['deletions'],
            'commit_hashes': ', '.join(stats['commit_hashes'])
        })
    
    # Create DataFrame and sort by total changes
    author_df = pd.DataFrame(author_stats).sort_values('total_changes', ascending=False)
    
    # Export author stats to CSV
    csv_file = f"author_contributions_{start_date}_to_{end_date}.csv"
    author_df.to_csv(csv_file, index=False)
    print(f"Author statistics exported to {csv_file}")
    
    # Print detailed author statistics
    print("\nAuthor contributions (includes PRs merged by others):")
    print("-------------------------------------------")
    print("| {:<25} | {:>8} | {:>10} | {:>10} | {:>10} |".format(
        "Name", "Commits", "Additions", "Deletions", "Total"))
    print("|------------------------------|----------|------------|------------|------------|")
    
    for _, author in author_df.iterrows():
        print("| {:<25} | {:>8} | {:>10} | {:>10} | {:>10} |".format(
            author['name'][:25], 
            author['commits'], 
            int(author['additions']), 
            int(author['deletions']), 
            int(author['total_changes'])
        ))
    
    print("-------------------------------------------")
    print(f"Total authors: {len(author_df)}")
    print("\nNOTE: This analysis properly attributes changes to the author, not just the committer.")
    print("      This ensures PR contributions are counted correctly.")

if __name__ == '__main__':
    main()
