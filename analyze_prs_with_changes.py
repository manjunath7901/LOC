#!/usr/bin/env python3
"""
Script to analyze PRs and their associated changes
This improved script properly connects PRs to their actual code changes
"""
import requests
import json
import sys
import datetime
import re

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
    
    # API Headers
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Analyzing repository between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
    
    # Step 1: Get all commits in the date range
    all_commits = get_all_commits(base_url, headers, workspace, repo_slug, start_date, end_date)
    
    if not all_commits:
        print("No commits found in the date range.")
        return
        
    print(f"Found {len(all_commits)} commits in the date range")
    
    # Step 2: Identify PRs and normal commits
    prs = []
    normal_commits = []
    
    for commit in all_commits:
        commit_id = commit['id']
        message = commit.get('message', '')
        
        # Check if this is a PR merge commit
        is_pr = "pull request" in message.lower() or "pr #" in message.lower()
        
        if is_pr:
            # Extract PR information
            pr_info = extract_pr_info(message)
            
            if pr_info:
                prs.append({
                    "commit": commit,
                    "pr_number": pr_info['number'],
                    "pr_title": pr_info['title'],
                    "associated_commits": [],  # Will be populated later
                    "additions": 0,
                    "deletions": 0,
                    "stats_found": False
                })
            else:
                # PR detection failed, treat as normal commit
                normal_commits.append(commit)
        else:
            # Not a PR merge commit
            normal_commits.append(commit)
    
    # Step 3: Associate normal commits with PRs based on commit message and timing
    for pr in prs:
        pr_title = pr['pr_title'].lower()
        pr_keywords = extract_keywords(pr_title)
        pr_commit_time = pr['commit'].get('authorTimestamp', 0)
        
        # Look for commits with matching keywords that happened before this PR
        for commit in normal_commits:
            commit_message = commit.get('message', '').lower()
            commit_time = commit.get('authorTimestamp', 0)
            
            # Check if this commit happened before the PR and has matching keywords
            if commit_time <= pr_commit_time and any(keyword in commit_message for keyword in pr_keywords):
                pr['associated_commits'].append(commit)
    
    # Step 4: Get line changes for PRs
    for pr in prs:
        # First try to get stats directly from PR commit
        pr_commit_id = pr['commit']['id']
        stats = get_commit_stats(base_url, headers, workspace, repo_slug, pr_commit_id)
        
        if stats['additions'] > 0 or stats['deletions'] > 0:
            pr['additions'] = stats['additions']
            pr['deletions'] = stats['deletions']
            pr['stats_found'] = True
        else:
            # If no changes in PR commit, check associated commits
            for commit in pr['associated_commits']:
                commit_id = commit['id']
                stats = get_commit_stats(base_url, headers, workspace, repo_slug, commit_id)
                pr['additions'] += stats['additions']
                pr['deletions'] += stats['deletions']
                
            if pr['additions'] > 0 or pr['deletions'] > 0:
                pr['stats_found'] = True
    
    # Step 5: Output the results, focusing on PRs
    print("\n" + "="*80)
    print("PULL REQUEST ANALYSIS RESULTS")
    print("="*80)
    
    for i, pr in enumerate(prs, 1):
        pr_commit = pr['commit']
        author_name = pr_commit.get('author', {}).get('displayName', 'Unknown')
        committer_name = pr_commit.get('committer', {}).get('displayName', 'Unknown')
        timestamp = pr_commit.get('authorTimestamp', 0)
        date = datetime.datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\nPR #{i}: {pr['pr_number']} - {date}")
        print(f"Title: {pr['pr_title']}")
        print(f"Author: {author_name} (merged by: {committer_name})")
        
        # Highlight if this is by Manjunath Kallatti
        is_manjunath = author_name == "Kallatti, Manjunath" or committer_name == "Kallatti, Manjunath"
        if is_manjunath:
            print("⭐️ THIS PR INVOLVES MANJUNATH KALLATTI ⭐️")
            
        # Print line changes
        if pr['stats_found']:
            print(f"Lines changed: +{pr['additions']}, -{pr['deletions']}, total: {pr['additions'] + pr['deletions']}")
        else:
            print("Lines changed: No changes found")
        
        # Show associated commits
        if pr['associated_commits']:
            print(f"Associated commits: {len(pr['associated_commits'])}")
            for j, commit in enumerate(pr['associated_commits'], 1):
                commit_id = commit['id'][:8]
                commit_author = commit.get('author', {}).get('displayName', 'Unknown')
                commit_message = commit.get('message', '').split('\n')[0][:50]
                print(f"  {j}. [{commit_id}] by {commit_author}: {commit_message}")
        else:
            print("Associated commits: None found")
    
    # Step 6: Provide summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    manjunath_prs = [pr for pr in prs if 
                     pr['commit'].get('author', {}).get('displayName') == "Kallatti, Manjunath" or 
                     pr['commit'].get('committer', {}).get('displayName') == "Kallatti, Manjunath"]
    
    total_lines_added = sum(pr['additions'] for pr in prs)
    total_lines_deleted = sum(pr['deletions'] for pr in prs)
    manjunath_lines_added = sum(pr['additions'] for pr in manjunath_prs)
    manjunath_lines_deleted = sum(pr['deletions'] for pr in manjunath_prs)
    
    print(f"Total PRs: {len(prs)}")
    print(f"PRs by/involving Manjunath Kallatti: {len(manjunath_prs)}")
    print(f"Total lines changed: +{total_lines_added}, -{total_lines_deleted}, total: {total_lines_added + total_lines_deleted}")
    print(f"Lines changed by Manjunath PRs: +{manjunath_lines_added}, -{manjunath_lines_deleted}, total: {manjunath_lines_added + manjunath_lines_deleted}")
    
    print("\nUser Contributions (PRs):")
    # Group by PR author
    author_stats = {}
    for pr in prs:
        author = pr['commit'].get('author', {}).get('displayName', 'Unknown')
        if author not in author_stats:
            author_stats[author] = {
                'prs': 0,
                'additions': 0,
                'deletions': 0
            }
        author_stats[author]['prs'] += 1
        author_stats[author]['additions'] += pr['additions']
        author_stats[author]['deletions'] += pr['deletions']
    
    # Sort by total changes
    sorted_authors = sorted(author_stats.items(), 
                           key=lambda x: x[1]['additions'] + x[1]['deletions'],
                           reverse=True)
    
    print("| {:<25} | {:>5} | {:>10} | {:>10} | {:>10} |".format(
        "Author", "PRs", "Additions", "Deletions", "Total"))
    print("|" + "-"*27 + "|" + "-"*7 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*12 + "|")
    
    for author, stats in sorted_authors:
        total_changes = stats['additions'] + stats['deletions']
        print("| {:<25} | {:>5} | {:>10} | {:>10} | {:>10} |".format(
            author, stats['prs'], stats['additions'], stats['deletions'], total_changes))

def get_all_commits(base_url, headers, workspace, repo_slug, start_date, end_date):
    """Get all commits in the given date range"""
    start_timestamp_ms = int(start_date.timestamp() * 1000)
    end_timestamp_ms = int(end_date.timestamp() * 1000)
    
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
            return []
        
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
            
    return filtered_commits

def extract_pr_info(message):
    """Extract PR number and title from commit message"""
    # Format: Pull request #1234: Title
    pr_pattern = r"[Pp]ull [Rr]equest #(\d+):\s*(.*)"
    match = re.search(pr_pattern, message)
    
    if match:
        return {
            'number': match.group(1),
            'title': match.group(2).strip()
        }
    return None

def extract_keywords(text):
    """Extract key words from text for matching"""
    text = text.lower()
    # Remove common words
    stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'for', 'in', 'to', 'with'}
    words = re.findall(r'\b\w+\b', text)
    keywords = [word for word in words if word not in stopwords and len(word) > 2]
    
    # Also add any issue numbers (e.g., CNX-12345)
    issues = re.findall(r'[A-Za-z]+-\d+', text)
    keywords.extend([issue.lower() for issue in issues])
    
    return keywords

def get_commit_stats(base_url, headers, workspace, repo_slug, commit_id):
    """Get line additions/deletions for a commit"""
    diff_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}/diff"
    response = requests.get(diff_url, headers=headers)
    
    if response.status_code != 200:
        return {'additions': 0, 'deletions': 0}
    
    diff_data = response.json()
    diffs = diff_data.get('diffs', [])
    
    additions = 0
    deletions = 0
    
    for diff in diffs:
        for hunk in diff.get('hunks', []):
            for segment in hunk.get('segments', []):
                if segment.get('type') == 'ADDED':
                    additions += len(segment.get('lines', []))
                elif segment.get('type') == 'REMOVED':
                    deletions += len(segment.get('lines', []))
    
    return {'additions': additions, 'deletions': deletions}

if __name__ == '__main__':
    main()
