#!/usr/bin/env python3
"""
Script to find all PRs from a specific member in the last week
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
    member_name = "Kallatti, Manjunath"
    member_email = "manjunath.kallatti@hpe.com"
    
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
    
    print(f"\nSearching for PRs by {member_name} between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
    
    # First, get all commits by this author in the date range
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
        
        # Filter commits by author and date
        for commit in commits:
            author = commit.get('author', {})
            author_name = author.get('displayName', '')
            author_email = author.get('emailAddress', '')
            
            # Also check committer in case they committed directly
            committer = commit.get('committer', {})
            committer_name = committer.get('displayName', '')
            committer_email = committer.get('emailAddress', '')
            
            # Check if this is our target member
            is_target_author = (author_name == member_name or author_email == member_email)
            is_target_committer = (committer_name == member_name or committer_email == member_email)
            
            if is_target_author or is_target_committer:
                # Get timestamp from author or committer
                timestamp_ms = commit.get('authorTimestamp', 0)
                if timestamp_ms >= start_timestamp_ms and timestamp_ms <= end_timestamp_ms:
                    all_commits.append(commit)
        
        # Check if there are more commits
        if not data.get('isLastPage', True):
            start = data.get('nextPageStart', 0)
        else:
            break
    
    if not all_commits:
        print(f"No commits found by {member_name} in the date range.")
        return
    
    print(f"\nFound {len(all_commits)} commits by {member_name}:")
    
    for idx, commit in enumerate(all_commits, 1):
        commit_id = commit['id']
        short_id = commit_id[:8]
        message = commit.get('message', '').split('\n')[0]  # Get first line of commit message
        timestamp = commit.get('authorTimestamp', 0)
        date = datetime.datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if this is a PR merge commit by looking at the message
        is_pr = "pull request" in message.lower() or "pr #" in message.lower()
        pr_marker = "[PR]" if is_pr else ""
        
        # Determine if this is a PR authored or merged
        author_name = commit.get('author', {}).get('displayName', 'Unknown')
        committer_name = commit.get('committer', {}).get('displayName', 'Unknown')
        
        if author_name == member_name and committer_name != member_name:
            pr_type = "PR Authored (merged by someone else)"
        elif author_name != member_name and committer_name == member_name:
            pr_type = "PR Merged (authored by someone else)"
        else:
            pr_type = "Direct commit"
            
        print(f"{idx}. {short_id} - {date} - {pr_marker} {pr_type}")
        print(f"   Message: {message}")
        
        # Get the diff details
        diff_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}/diff"
        diff_response = requests.get(diff_url, headers=headers)
        
        if diff_response.status_code == 200:
            diff_data = diff_response.json()
            diffs = diff_data.get('diffs', [])
            
            if not diffs:
                print("   NO CHANGES FOUND IN DIFF - This could be a merge commit with no changes")
                # Try to get file changes in a different way
                try:
                    files_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}/changes"
                    files_response = requests.get(files_url, headers=headers)
                    if files_response.status_code == 200:
                        files_data = files_response.json()
                        values = files_data.get('values', [])
                        if values:
                            print(f"   But found {len(values)} changed files via changes API")
                            for file in values[:3]:  # Just show first 3
                                path = file.get('path', {}).get('toString', '')
                                print(f"   - {path}")
                            if len(values) > 3:
                                print(f"   - ...and {len(values) - 3} more files")
                except Exception as e:
                    print(f"   Error checking file changes: {e}")
            else:
                print(f"   Found {len(diffs)} changed files")
                for diff in diffs[:3]:  # Just show first 3
                    path = diff.get('destination', {}).get('toString', '')
                    print(f"   - {path}")
                if len(diffs) > 3:
                    print(f"   - ...and {len(diffs) - 3} more files")
                    
    print("\nNote: PRs may show 0 lines changed in the LOC analyzer if:")
    print("1. They are merge commits with no direct code changes")
    print("2. The changes were already counted in another commit")
    print("3. The changes are to binary files or are whitespace-only")
    print("4. There is an issue retrieving the diff from the API")

if __name__ == '__main__':
    main()
