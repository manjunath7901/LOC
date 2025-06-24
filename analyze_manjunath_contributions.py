#!/usr/bin/env python3
"""
Script to analyze Manjunath Kallatti's contributions in the CX Switch Health repository
including both PRs and direct commits
"""

from bitbucket_loc_analyzer import BitbucketLOCAnalyzer
from datetime import datetime

def main():
    # Configuration
    token = "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V"  # Replace with your token if needed
    base_url = "https://stash.arubanetworks.com"
    workspace = "GVT"
    repo_slug = "cx-switch-health-read-assist"
    start_date = "2025-06-01"
    end_date = "2025-06-24"
    target_user = "Kallatti, Manjunath"
    
    # Create analyzer instance
    analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
    
    # Test connection
    print(f"Testing connection to Bitbucket server...")
    if not analyzer.test_connection(workspace, repo_slug):
        print("Connection failed. Check your credentials and network.")
        return
    
    # Get all commits in date range
    print(f"Fetching commits from {start_date} to {end_date}...")
    commits = analyzer.get_commits(workspace, repo_slug, start_date=start_date, end_date=end_date)
    
    # Filter commits by target user
    manjunath_commits = []
    for commit in commits:
        author_name = commit.get('author', {}).get('displayName', 'Unknown')
        if target_user in author_name:
            manjunath_commits.append(commit)
    
    print(f"Found {len(manjunath_commits)} commits by {target_user}")
    
    # Analyze each commit
    total_additions = 0
    total_deletions = 0
    
    print("\nDetailed commit analysis:")
    print("=" * 80)
    for commit in manjunath_commits:
        commit_id = commit['id']
        commit_date = datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000)
        message = commit.get('message', '').split('\n')[0]  # First line only
        
        # Get change statistics for this commit
        stats = analyzer.get_loc_changes(workspace, repo_slug, commit_id)
        
        additions = stats.get('additions', 0)
        deletions = stats.get('deletions', 0)
        
        print(f"Date: {commit_date.strftime('%Y-%m-%d')}")
        print(f"ID: {commit_id[:8]}")
        print(f"Message: {message}")
        print(f"Additions: {additions}, Deletions: {deletions}, Total: {additions + deletions}")
        print("-" * 80)
        
        total_additions += additions
        total_deletions += deletions
    
    print("\nSummary:")
    print(f"Total commits by {target_user}: {len(manjunath_commits)}")
    print(f"Total additions: {total_additions}")
    print(f"Total deletions: {total_deletions}")
    print(f"Total changes: {total_additions + total_deletions}")
    
    # Check for commit on June 12 specifically
    june12_commits = []
    for commit in manjunath_commits:
        commit_date = datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000)
        if commit_date.strftime('%Y-%m-%d') == '2025-06-12':
            june12_commits.append(commit)
    
    if june12_commits:
        print("\nJune 12, 2025 commits:")
        print("=" * 80)
        for commit in june12_commits:
            commit_id = commit['id']
            commit_date = datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000)
            message = commit.get('message', '').split('\n')[0]  # First line only
            
            # Get change statistics for this commit
            stats = analyzer.get_loc_changes(workspace, repo_slug, commit_id)
            
            additions = stats.get('additions', 0)
            deletions = stats.get('deletions', 0)
            
            print(f"Date: {commit_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"ID: {commit_id[:8]}")
            print(f"Message: {message}")
            print(f"Additions: {additions}, Deletions: {deletions}, Total: {additions + deletions}")
            
            # Check if this is a PR or direct commit
            is_pr = "pull request" in message.lower() or "pr #" in message.lower()
            print(f"Type: {'PR merge' if is_pr else 'Direct commit'}")
            print("-" * 80)
    else:
        print("\nNo commits found on June 12, 2025")

if __name__ == '__main__':
    main()
