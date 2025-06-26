#!/usr/bin/env python3
import requests
import json
import sys
import datetime
from datetime import datetime, timedelta

# Configuration
token_file = "~/.bitbucket_token"
try:
    with open(token_file.replace("~", "/Users/kallatti"), 'r') as f:
        token = f.read().strip()
except:
    token = "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V"

base_url = "https://stash.arubanetworks.com"
workspace = "GVT"
repo_slug = "cx-switch-health-read-assist"
headers = {"Authorization": f"Bearer {token}"}

# Calculate date 14 days ago
end_date = datetime.now()
start_date = end_date - timedelta(days=14)
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

print(f"Analyzing repository between {start_date_str} and {end_date_str}")

# Get all commits
url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
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
        commit_date = datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000)
        if start_date <= commit_date <= end_date:
            all_commits.append(commit)
            
    is_last_page = data.get('isLastPage', True)
    if is_last_page:
        break
    
    params['start'] = data.get('nextPageStart')

print(f"Found {len(all_commits)} commits in the date range")

# Print details for each commit
for commit in all_commits:
    commit_id = commit.get('id')
    author_name = commit.get('author', {}).get('displayName', 'Unknown')
    author_email = commit.get('author', {}).get('emailAddress', 'Unknown')
    commit_date = datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000)
    message = commit.get('message', '').split('\n')[0]  # First line only
    
    print(f"Commit: {commit_id[:8]}, Author: {author_name}, Date: {commit_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Email: {author_email}")
    print(f"  Message: {message}")
    
    # Check if this is a PR merge commit
    is_pr = "pull request" in message.lower() or "pr #" in message.lower() or "merge pull request" in message.lower()
    print(f"  Is PR: {is_pr}")
    
    # Print parent commits info
    parents = commit.get('parents', [])
    print(f"  Parents: {len(parents)}")
    
    print(f"  Date: {datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000).strftime('%Y-%m-%d')}")
    print()

# Check for June 12 commits specifically
print("\n=== JUNE 12 COMMITS ===")
june12_commits = [c for c in all_commits if datetime.fromtimestamp(c.get('authorTimestamp', 0) / 1000).strftime('%Y-%m-%d') == '2025-06-12']
print(f"Found {len(june12_commits)} commits on June 12, 2025")

for commit in june12_commits:
    commit_id = commit.get('id')
    author_name = commit.get('author', {}).get('displayName', 'Unknown')
    message = commit.get('message', '').split('\n')[0]  # First line only
    
    # Get detailed info about this commit
    diff_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}/diff"
    diff_response = requests.get(diff_url, headers=headers)
    
    additions = 0
    deletions = 0
    
    if diff_response.status_code == 200:
        diff_data = diff_response.json()
        for diff_file in diff_data.get('diffs', []):
            file_path = diff_file.get('destination', {}).get('toString', '')
            print(f"  File: {file_path}")
            
            for hunk in diff_file.get('hunks', []):
                for segment in hunk.get('segments', []):
                    if segment.get('type') == 'ADDED':
                        additions += len(segment.get('lines', []))
                    elif segment.get('type') == 'REMOVED':
                        deletions += len(segment.get('lines', []))
    
    print(f"  Commit: {commit_id[:8]}, Author: {author_name}")
    print(f"  Message: {message}")
    print(f"  Additions: {additions}, Deletions: {deletions}")
    print()
