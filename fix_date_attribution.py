#!/usr/bin/env python3
"""
Fixed LOC Attribution Tool for Bitbucket

This script analyzes a Bitbucket repository to track lines of code added and deleted over time,
with proper attribution to authors regardless of whether they used PRs or direct commits.
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import csv
import os
from dateutil.parser import parse
import sys

def main():
    # Configuration
    token_file = os.path.expanduser("~/.bitbucket_token")
    with open(token_file, 'r') as f:
        token = f.read().strip()
    
    base_url = "https://stash.arubanetworks.com"
    api_base = base_url  
    workspace = "GVT"
    repo_slug = "cx-switch-health-read-assist"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get date range from command line or use defaults
    start_date_str = sys.argv[1] if len(sys.argv) > 1 else None
    end_date_str = sys.argv[2] if len(sys.argv) > 2 else None
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
    else:
        # Default to last 14 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
    
    print(f"Analyzing repository between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
    
    # Get all commits in the date range PLUS 14 extra days
    extended_start_date = start_date - timedelta(days=14)  # Look back further for commits
    
    # Convert to timestamps for API
    start_timestamp = int(extended_start_date.timestamp() * 1000)
    end_timestamp = int(end_date.timestamp() * 1000)
    
    # Get all commits (including those from before our date range)
    url = f"{api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
    params = {'limit': 100, 'start': 0}
    
    all_commits = []
    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            sys.exit(1)
        
        data = response.json()
        commits = data.get('values', [])
        
        for commit in commits:
            timestamp = commit.get('authorTimestamp', 0)
            if start_timestamp <= timestamp <= end_timestamp:
                all_commits.append(commit)
                
        is_last_page = data.get('isLastPage', True)
        if is_last_page or len(all_commits) > 500:  # Limit to 500 commits max
            break
        
        params['start'] = data.get('nextPageStart')
    
    print(f"Found {len(all_commits)} commits to analyze (including history)")
    
    # Analyze each commit to get:
    # 1. Its actual contribution date (when the REAL code was written)
    # 2. Its actual author (who REALLY wrote the code)
    # 3. Its LOC changes (additions, deletions)
    
    commit_data = []
    pr_data = {}  # To store PR information
    pr_commits = set()  # To track commits that are part of PRs
    direct_commits = []
    
    # First pass: Identify all PRs and direct commits
    for commit in all_commits:
        commit_id = commit.get('id')
        message = commit.get('message', '')
        author_name = commit.get('author', {}).get('displayName', 'Unknown')
        author_email = commit.get('author', {}).get('emailAddress', 'Unknown')
        timestamp = commit.get('authorTimestamp', 0)
        commit_date = datetime.fromtimestamp(timestamp / 1000)
        
        # Check if this is a PR merge commit
        is_pr = "pull request" in message.lower() or "pr #" in message.lower() or "merge pull request" in message.lower()
        
        if is_pr:
            # Extract PR number
            import re
            pr_match = re.search(r'#(\d+)', message)
            pr_number = pr_match.group(1) if pr_match else "unknown"
            pr_title = message.split(':', 1)[1].strip() if ':' in message else message
            
            pr_data[pr_number] = {
                'commit_id': commit_id,
                'title': pr_title,
                'author': author_name,
                'email': author_email,
                'date': commit_date,
                'associated_commits': [],
                'additions': 0,
                'deletions': 0,
                'source_commit': None  # Will store the actual implementation commit
            }
            
            # Look at parent commits to identify the implementation
            parents = commit.get('parents', [])
            if len(parents) >= 2:
                # First parent is usually target branch, second is PR branch
                pr_branch_parent_id = parents[1]['id']
                
                # Find this commit in our list
                for c in all_commits:
                    if c['id'] == pr_branch_parent_id:
                        pr_data[pr_number]['source_commit'] = c
                        pr_commits.add(pr_branch_parent_id)
                        break
        else:
            # This is a direct commit
            direct_commits.append(commit)
    
    # Remove PR source commits from direct commits list
    direct_commits = [c for c in direct_commits if c['id'] not in pr_commits]
    
    # Second pass: Calculate LOC changes for each commit
    commit_changes = {}  # To store LOC changes
    
    # Process all commits to get LOC changes
    for commit in all_commits:
        commit_id = commit.get('id')
        author_name = commit.get('author', {}).get('displayName', 'Unknown')
        timestamp = commit.get('authorTimestamp', 0)
        commit_date = datetime.fromtimestamp(timestamp / 1000)
        
        # Get the commit diff to calculate additions and deletions
        diff_url = f"{api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}/diff"
        diff_response = requests.get(diff_url, headers=headers)
        
        additions = 0
        deletions = 0
        
        if diff_response.status_code == 200:
            diff_data = diff_response.json()
            for diff_file in diff_data.get('diffs', []):
                for hunk in diff_file.get('hunks', []):
                    for segment in hunk.get('segments', []):
                        if segment.get('type') == 'ADDED':
                            additions += len(segment.get('lines', []))
                        elif segment.get('type') == 'REMOVED':
                            deletions += len(segment.get('lines', []))
        
        # Store commit changes
        commit_changes[commit_id] = {
            'author': author_name,
            'date': commit_date,
            'additions': additions,
            'deletions': deletions
        }
    
    # Update PR data with the actual changes from source commits
    for pr_number, pr in pr_data.items():
        if pr['source_commit']:
            source_id = pr['source_commit']['id']
            if source_id in commit_changes:
                # Attribution fix: Use the ACTUAL author and date from the source commit
                original_author = pr['source_commit'].get('author', {}).get('displayName', 'Unknown')
                original_date = datetime.fromtimestamp(pr['source_commit'].get('authorTimestamp', 0) / 1000)
                
                pr['additions'] = commit_changes[source_id]['additions'] 
                pr['deletions'] = commit_changes[source_id]['deletions']
                pr['original_author'] = original_author
                pr['original_date'] = original_date
    
    # Generate time-based statistics (by day)
    date_stats = {}
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Initialize all days
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        date_stats[date_str] = {'additions': 0, 'deletions': 0}
        current_date += timedelta(days=1)
    
    # Add PR contributions
    for pr_number, pr in pr_data.items():
        if 'original_date' in pr and start_date <= pr['original_date'] <= end_date:
            date_str = pr['original_date'].strftime('%Y-%m-%d')
            date_stats[date_str]['additions'] += pr['additions']
            date_stats[date_str]['deletions'] += pr['deletions']
    
    # Add direct commit contributions
    for commit in direct_commits:
        commit_id = commit['id']
        if commit_id in commit_changes:
            commit_date = commit_changes[commit_id]['date']
            if start_date <= commit_date <= end_date:
                date_str = commit_date.strftime('%Y-%m-%d')
                date_stats[date_str]['additions'] += commit_changes[commit_id]['additions']
                date_stats[date_str]['deletions'] += commit_changes[commit_id]['deletions']
    
    # Create CSV with daily statistics
    with open('fixed_daily_stats.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'additions', 'deletions', 'total_changes'])
        for date_str, stats in sorted(date_stats.items()):
            writer.writerow([
                date_str, 
                stats['additions'], 
                stats['deletions'], 
                stats['additions'] + stats['deletions']
            ])
    
    print("Created fixed_daily_stats.csv")
    
    # Generate user statistics
    user_stats = {}
    
    # Add PR contributions
    for pr_number, pr in pr_data.items():
        if 'original_date' in pr and start_date <= pr['original_date'] <= end_date:
            # Use the original author
            author = pr.get('original_author', pr['author'])
            email = pr['email']
            
            if author not in user_stats:
                user_stats[author] = {
                    'name': author,
                    'email': email,
                    'additions': 0,
                    'deletions': 0,
                    'total_changes': 0,
                    'commits': 0,
                    'prs': 0,
                    'direct_commits': 0
                }
            
            user_stats[author]['additions'] += pr['additions']
            user_stats[author]['deletions'] += pr['deletions']
            user_stats[author]['total_changes'] += pr['additions'] + pr['deletions']
            user_stats[author]['commits'] += 1
            user_stats[author]['prs'] += 1
    
    # Add direct commit contributions
    for commit in direct_commits:
        commit_id = commit['id']
        if commit_id in commit_changes:
            commit_date = commit_changes[commit_id]['date']
            if start_date <= commit_date <= end_date:
                author = commit.get('author', {}).get('displayName', 'Unknown')
                email = commit.get('author', {}).get('emailAddress', 'Unknown')
                
                if author not in user_stats:
                    user_stats[author] = {
                        'name': author,
                        'email': email,
                        'additions': 0,
                        'deletions': 0,
                        'total_changes': 0,
                        'commits': 0,
                        'prs': 0,
                        'direct_commits': 0
                    }
                
                user_stats[author]['additions'] += commit_changes[commit_id]['additions']
                user_stats[author]['deletions'] += commit_changes[commit_id]['deletions']
                user_stats[author]['total_changes'] += commit_changes[commit_id]['additions'] + commit_changes[commit_id]['deletions']
                user_stats[author]['commits'] += 1
                user_stats[author]['direct_commits'] += 1
    
    # Create CSV with user statistics
    with open('fixed_user_stats.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'email', 'commits', 'prs', 'direct_commits', 'additions', 'deletions', 'total_changes'])
        
        # Sort by total changes
        sorted_users = sorted(user_stats.values(), key=lambda x: x['total_changes'], reverse=True)
        
        for user in sorted_users:
            writer.writerow([
                user['name'],
                user['email'],
                user['commits'],
                user['prs'],
                user['direct_commits'],
                user['additions'],
                user['deletions'],
                user['total_changes']
            ])
    
    print("Created fixed_user_stats.csv")
    
    # Create visualization for daily changes
    dates = []
    additions = []
    deletions = []
    
    for date_str, stats in sorted(date_stats.items()):
        if stats['additions'] > 0 or stats['deletions'] > 0:
            dates.append(date_str)
            additions.append(stats['additions'])
            deletions.append(stats['deletions'])
    
    plt.figure(figsize=(12, 6))
    plt.bar(dates, additions, color='green', alpha=0.7, label='Additions')
    plt.bar(dates, [-d for d in deletions], color='red', alpha=0.7, label='Deletions')
    plt.title(f'Code Changes in {workspace}/{repo_slug}')
    plt.xlabel('Date')
    plt.ylabel('Lines of Code')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('fixed_daily_changes.png')
    
    print("Created fixed_daily_changes.png")
    
    # Print top contributors
    print("\nTop Contributors:")
    for i, user in enumerate(sorted_users[:5], 1):
        print(f"{i}. {user['name']} - {user['additions']} additions, {user['deletions']} deletions, {user['total_changes']} total changes")
        print(f"   PRs: {user['prs']}, Direct Commits: {user['direct_commits']}")

if __name__ == "__main__":
    main()
