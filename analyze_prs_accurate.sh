#!/bin/bash

# Calculate date 7 days ago in YYYY-MM-DD format
START_DATE=$(date -v-7d +"%Y-%m-%d")
END_DATE=$(date +"%Y-%m-%d")

echo "Analyzing PRs and their associated changes from $START_DATE to $END_DATE (last week)"
echo "IMPROVED VERSION - Ensures each commit is only counted once"

# Create a script to analyze PRs and their associated changes
cat > analyze_prs_accurate.py << 'EOF'
#!/usr/bin/env python3
"""
Script to analyze PRs and their associated changes with improved accuracy
This script ensures each commit's changes are only counted for one PR
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
    
    # Step 2: Inspect each commit to see if it's a PR merge commit
    prs = []
    normal_commits = []
    commit_id_to_pr_map = {}  # Maps commit IDs to PRs for quick lookup
    
    for commit in all_commits:
        commit_id = commit['id']
        message = commit.get('message', '')
        
        # Check if this is a PR merge commit
        is_pr = "pull request" in message.lower() or "pr #" in message.lower()
        
        if is_pr:
            # Extract PR information
            pr_info = extract_pr_info(message)
            if pr_info:
                pr = {
                    "commit": commit,
                    "pr_number": pr_info['number'],
                    "pr_title": pr_info['title'],
                    "direct_changes": {},  # Will store direct changes in the PR commit
                    "associated_commits": []  # Will be populated with commits specific to this PR
                }
                prs.append(pr)
                
                # Map this commit to its PR
                commit_id_to_pr_map[commit_id] = pr
            else:
                # PR detection failed, treat as normal commit
                normal_commits.append(commit)
        else:
            # Not a PR merge commit
            normal_commits.append(commit)
    
    # Step 3: Directly analyze each PR merge commit
    for pr in prs:
        pr_commit_id = pr['commit']['id']
        stats = get_commit_stats(base_url, headers, workspace, repo_slug, pr_commit_id)
        pr['direct_changes'] = stats
    
    # Step 4: For PR merge commits with no direct changes, find the actual commits
    # Sort PRs by timestamp, oldest first, so we associate commits with the right PR
    prs.sort(key=lambda x: x['commit'].get('authorTimestamp', 0))
    
    # First, get direct parent commits for the PRs
    for pr in prs:
        pr_commit = pr['commit']
        parents = pr_commit.get('parents', [])
        
        if parents:
            # Try to get the parent commit to see changes
            parent_id = parents[0].get('id', '')
            if parent_id:
                print(f"Checking parents for PR #{pr['pr_number']}")
                # Check if the parent is in our date range
                parent_in_range = False
                for commit in all_commits:
                    if commit['id'] == parent_id:
                        parent_in_range = True
                        break
                        
                if not parent_in_range:
                    # Fetch the parent commit directly
                    parent_commit = get_commit(base_url, headers, workspace, repo_slug, parent_id)
                    if parent_commit:
                        all_commits.append(parent_commit)
                        normal_commits.append(parent_commit)
    
    # Track which commits have been assigned to PRs
    assigned_commits = set()
    
    # Assign commits to PRs based on timeframe and content matching
    for pr in prs:
        pr_title = pr['pr_title'].lower()
        pr_number = pr['pr_number']
        pr_keywords = extract_keywords(pr_title)
        pr_commit_time = pr['commit'].get('authorTimestamp', 0)
        
        # Extract PR issue number (e.g., CNX-12345)
        pr_issue = extract_issue_number(pr_title)
        
        # Get PR author to match commits from the same author
        pr_author = pr['commit'].get('author', {}).get('displayName', '').lower()
        
        print(f"\nAssigning commits to PR #{pr_number}: {pr_title}")
        print(f"  Keywords: {pr_keywords}")
        print(f"  Issue: {pr_issue}")
        print(f"  Author: {pr_author}")
        
        for commit in normal_commits:
            commit_id = commit['id']
            
            # Skip if already assigned
            if commit_id in assigned_commits:
                continue
                
            commit_message = commit.get('message', '').lower()
            commit_time = commit.get('authorTimestamp', 0)
            commit_author = commit.get('author', {}).get('displayName', '').lower()
            
            # Only consider commits before the PR merge
            if commit_time > pr_commit_time:
                continue
                
            # Check for match criteria
            match_reasons = []
            
            # 1. Check if same issue number
            if pr_issue and pr_issue in commit_message:
                match_reasons.append(f"Issue match: {pr_issue}")
            
            # 2. Check if same author
            if pr_author and commit_author == pr_author:
                match_reasons.append(f"Author match: {pr_author}")
                
            # 3. Check for keyword matches
            keyword_matches = [kw for kw in pr_keywords if kw in commit_message]
            if keyword_matches:
                match_reasons.append(f"Keywords: {', '.join(keyword_matches)}")
                
            # 4. Check for title similarity
            if similar_strings(pr_title, commit_message, threshold=0.7):
                match_reasons.append("Title similarity")
                
            # If we have good matches, assign this commit to the PR
            if len(match_reasons) >= 1:  # Require at least one match reason
                print(f"  Assigning commit {commit_id[:8]} to PR #{pr_number}")
                print(f"    Message: {commit_message[:50]}...")
                print(f"    Reasons: {', '.join(match_reasons)}")
                pr['associated_commits'].append({
                    'commit': commit,
                    'match_reasons': match_reasons
                })
                assigned_commits.add(commit_id)
    
    # Step 5: Get combined stats for each PR
    for pr in prs:
        # Start with direct changes from PR commit
        additions = pr['direct_changes'].get('additions', 0)
        deletions = pr['direct_changes'].get('deletions', 0)
        
        # Add changes from associated commits
        for associated in pr['associated_commits']:
            commit_id = associated['commit']['id']
            stats = get_commit_stats(base_url, headers, workspace, repo_slug, commit_id)
            additions += stats.get('additions', 0)
            deletions += stats.get('deletions', 0)
            
        # Store the totals
        pr['total_additions'] = additions
        pr['total_deletions'] = deletions
        pr['total_changes'] = additions + deletions
    
    # Step 6: Output the results, focusing on PRs
    print("\n" + "="*80)
    print("PULL REQUEST ANALYSIS RESULTS")
    print("="*80)
    
    # Sort PRs by date
    prs.sort(key=lambda x: x['commit'].get('authorTimestamp', 0))
    
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
        print(f"Lines changed: +{pr['total_additions']}, -{pr['total_deletions']}, total: {pr['total_changes']}")
        
        # Print direct changes in PR commit
        direct_add = pr['direct_changes'].get('additions', 0)
        direct_del = pr['direct_changes'].get('deletions', 0)
        print(f"  - Direct changes in PR commit: +{direct_add}, -{direct_del}")
        
        # Show associated commits
        if pr['associated_commits']:
            print(f"Associated commits: {len(pr['associated_commits'])}")
            for j, associated in enumerate(pr['associated_commits'], 1):
                commit = associated['commit']
                commit_id = commit['id'][:8]
                commit_author = commit.get('author', {}).get('displayName', 'Unknown')
                commit_message = commit.get('message', '').split('\n')[0][:50]
                
                # Get stats for this commit
                stats = get_commit_stats(base_url, headers, workspace, repo_slug, commit['id'])
                add = stats.get('additions', 0)
                delete = stats.get('deletions', 0)
                
                print(f"  {j}. [{commit_id}] by {commit_author}: +{add}, -{delete}")
                print(f"     Message: {commit_message}")
                print(f"     Match reasons: {', '.join(associated['match_reasons'])}")
        else:
            print("Associated commits: None found")
    
    # Step 7: Provide summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    manjunath_prs = [pr for pr in prs if 
                     pr['commit'].get('author', {}).get('displayName') == "Kallatti, Manjunath"]
    
    total_lines_added = sum(pr['total_additions'] for pr in prs)
    total_lines_deleted = sum(pr['total_deletions'] for pr in prs)
    manjunath_lines_added = sum(pr['total_additions'] for pr in manjunath_prs)
    manjunath_lines_deleted = sum(pr['total_deletions'] for pr in manjunath_prs)
    
    print(f"Total PRs: {len(prs)}")
    print(f"PRs by Manjunath Kallatti: {len(manjunath_prs)}")
    print(f"Total lines changed across all PRs: +{total_lines_added}, -{total_lines_deleted}, total: {total_lines_added + total_lines_deleted}")
    print(f"Lines changed in Manjunath PRs: +{manjunath_lines_added}, -{manjunath_lines_deleted}, total: {manjunath_lines_added + manjunath_lines_deleted}")
    
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
        author_stats[author]['additions'] += pr['total_additions']
        author_stats[author]['deletions'] += pr['total_deletions']
    
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

# Helper functions
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

def get_commit(base_url, headers, workspace, repo_slug, commit_id):
    """Get a specific commit by ID"""
    url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Warning: Couldn't fetch commit {commit_id}: {response.status_code}")
        return None
        
    return response.json()

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
    return keywords

def extract_issue_number(text):
    """Extract issue number like CNX-12345 from text"""
    match = re.search(r'[A-Za-z]+-\d+', text)
    return match.group(0) if match else None

def similar_strings(str1, str2, threshold=0.7):
    """Check if two strings are similar"""
    if not str1 or not str2:
        return False
        
    # Convert to sets of words
    words1 = set(extract_keywords(str1))
    words2 = set(extract_keywords(str2))
    
    if not words1 or not words2:
        return False
        
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    if union == 0:
        return False
        
    similarity = intersection / union
    return similarity >= threshold

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
EOF

# Make the script executable
chmod +x analyze_prs_accurate.py

# Run the script with start and end dates
python analyze_prs_accurate.py $START_DATE $END_DATE
