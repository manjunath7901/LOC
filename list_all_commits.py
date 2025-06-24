#!/usr/bin/env python3
"""
Script to list all commits in the last week with PR detection
"""
import requests
import json
import sys
import datetime

def main():
    # Configuration
    token = "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V"
    base_url = "https://stash.arubanetworks.com"
    workspace = "GVT"
    repo_slug = "cx-switch-health-read-assist"
    
    start_date_str = sys.argv[1] if len(sys.argv) > 1 else None
    end_date_str = sys.argv[2] if len(sys.argv) > 2 else None
    
    if start_date_str and end_date_str:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
    else:
        # Default to last week
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=7)
    
    # Convert to milliseconds
    start_timestamp_ms = int(start_date.timestamp() * 1000)
    end_timestamp_ms = int(end_date.timestamp() * 1000)
    
    # API Headers
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Listing all commits between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
    
    # Get all commits in the date range
    api_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
    params = {'limit': 100}
    
    all_commits = []
    start = 0
    
    while True:
        params['start'] = start
        response = requests.get(api_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        if 'values' not in data or not data['values']:
            break
        
        commits = data['values']
        all_commits.extend(commits)
        
        # Check if there are more commits
        if not data.get('isLastPage', True):
            start = data.get('nextPageStart', 0)
        else:
            break
    
    # Filter commits by date range
    filtered_commits = []
    for commit in all_commits:
        timestamp_ms = commit.get('authorTimestamp', 0)
        if timestamp_ms >= start_timestamp_ms and timestamp_ms <= end_timestamp_ms:
            filtered_commits.append(commit)
    
    if not filtered_commits:
        print("No commits found in the date range.")
        return
    
    print(f"\nFound {len(filtered_commits)} commits in the date range:")
    
    # Sort commits by timestamp
    filtered_commits.sort(key=lambda x: x.get('authorTimestamp', 0))
    
    # Process all PRs and normal commits
    prs = []
    normal_commits = []
    for commit in filtered_commits:
        commit_id = commit['id']
        short_id = commit_id[:8]
        message = commit.get('message', '').split('\n')[0]  # Get first line of commit message
        timestamp = commit.get('authorTimestamp', 0)
        date = datetime.datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get author and committer info
        author_name = commit.get('author', {}).get('displayName', 'Unknown')
        committer_name = commit.get('committer', {}).get('displayName', 'Unknown')
        
        # Is it a PR?
        is_pr = "pull request" in message.lower() or "pr #" in message.lower()
        
        # Special handling for commits from Kallatti, Manjunath
        is_manjunath_commit = (author_name == "Kallatti, Manjunath" or committer_name == "Kallatti, Manjunath")
        
        # Extract PR number if present
        pr_number = None
        if is_pr:
            # Try to extract PR number from message
            try:
                # Common format: Pull request #1234: Description
                if "pull request #" in message.lower():
                    pr_start = message.lower().index("pull request #") + 13
                    pr_end = message.index(":", pr_start)
                    pr_number = message[pr_start:pr_end].strip()
            except:
                pass
                
            entry = {
                "commit_id": short_id,
                "date": date,
                "author": author_name,
                "committer": committer_name,
                "message": message,
                "pr_number": pr_number,
                "is_manjunath_commit": is_manjunath_commit
            }
            prs.append(entry)
        else:
            entry = {
                "commit_id": short_id,
                "date": date,
                "author": author_name,
                "committer": committer_name,
                "message": message,
                "is_manjunath_commit": is_manjunath_commit
            }
            normal_commits.append(entry)
    
    # Print PRs first, then normal commits
    print("\nPull Requests:")
    print("-" * 80)
    for i, pr in enumerate(prs, 1):
        highlight = " 👉" if pr["is_manjunath_commit"] else ""
        print(f"{i}. [{pr['commit_id']}] {pr['date']} - PR #{pr['pr_number'] or '?'}{highlight}")
        print(f"   Author: {pr['author']} | Committer: {pr['committer']}")
        print(f"   Message: {pr['message']}")
    
    print("\nNormal Commits:")
    print("-" * 80)
    for i, commit in enumerate(normal_commits, 1):
        highlight = " 👉" if commit["is_manjunath_commit"] else ""
        print(f"{i}. [{commit['commit_id']}] {commit['date']}{highlight}")
        print(f"   Author: {commit['author']} | Committer: {commit['committer']}")
        print(f"   Message: {commit['message']}")
        
    print("\nSUMMARY:")
    print(f"- Total commits in period: {len(filtered_commits)}")
    print(f"- Pull requests: {len(prs)}")
    print(f"- Normal commits: {len(normal_commits)}")
    
    manjunath_prs = [pr for pr in prs if pr["is_manjunath_commit"]]
    print(f"- PRs by/involving Manjunath Kallatti: {len(manjunath_prs)}")

if __name__ == '__main__':
    main()
