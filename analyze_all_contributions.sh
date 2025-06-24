#!/bin/bash

# Calculate date 14 days ago in YYYY-MM-DD format
START_DATE=$(date -v-14d +"%Y-%m-%d")
END_DATE=$(date +"%Y-%m-%d")

echo "Analyzing member contributions from $START_DATE to $END_DATE (last 14 days)"

# Create a comprehensive script that analyzes ALL commits AND PRs
cat > analyze_all_contributions.py << 'EOF'
#!/usr/bin/env python3
"""
Script to analyze ALL contributions including both PRs and direct commits
This script combines the standard LOC analysis with PR-specific analysis
"""
import requests
import json
import sys
import datetime
import re
import csv
import os
import pandas as pd

def main():
    # Configuration
    token_file = os.path.expanduser("~/.bitbucket_token")
    with open(token_file, 'r') as f:
        token = f.read().strip()
        
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
        # Default to last two weeks
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=14)
    
    # API Headers
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Analyzing repository between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
    
    # Step 1: Get all commits in the date range
    all_commits = get_all_commits(base_url, headers, workspace, repo_slug, start_date, end_date)
    
    if not all_commits:
        print("No commits found in the date range.")
        return
        
    print(f"Found {len(all_commits)} commits in the date range")
    
    # Step 2: Identify PR merge commits vs. direct commits
    prs = []
    direct_commits = []
    processed_commits = set()  # Track which commits have been processed
    commit_id_to_pr_map = {}  # Maps commit IDs to PRs for quick lookup
    
    for commit in all_commits:
        commit_id = commit['id']
        message = commit.get('message', '')
        
        # Check if this is a PR merge commit
        is_pr = "pull request" in message.lower() or "pr #" in message.lower() or "merge pull request" in message.lower()
        
        if is_pr:
            # Extract PR information
            pr_info = extract_pr_info(message)
            if pr_info:
                pr = {
                    "commit": commit,
                    "pr_number": pr_info['number'],
                    "pr_title": pr_info['title'],
                    "author_name": commit.get('author', {}).get('displayName', 'Unknown'),
                    "author_email": commit.get('author', {}).get('emailAddress', 'Unknown'),
                    "direct_changes": {},  # Will store direct changes in the PR commit
                    "associated_commits": [],  # Will be populated with commits specific to this PR
                    "total_additions": 0,
                    "total_deletions": 0
                }
                prs.append(pr)
                
                # Mark this commit as processed
                processed_commits.add(commit_id)
                
                # Map this commit to its PR
                commit_id_to_pr_map[commit_id] = pr
            else:
                # PR detection failed, treat as direct commit
                direct_commits.append(commit)
        else:
            # Not a PR merge commit, definitely a direct commit
            direct_commits.append(commit)
    
    # Step 3: Directly analyze each PR merge commit for changes
    for pr in prs:
        pr_commit_id = pr['commit']['id']
        stats = get_commit_stats(base_url, headers, workspace, repo_slug, pr_commit_id)
        pr['direct_changes'] = stats
        pr['total_additions'] += stats.get('additions', 0)
        pr['total_deletions'] += stats.get('deletions', 0)
    
    # Step 4: For each PR, find all its associated commits
    # We need to get the parent and child commits to figure out the branch structure
    for pr in prs:
        pr_commit = pr['commit']
        pr_commit_id = pr_commit['id']
        
        # Get the PR's parent commits
        parents = pr_commit.get('parents', [])
        if len(parents) >= 2:  # Merge commits typically have 2 parents
            # The first parent is usually the target branch (e.g., main)
            # The second parent is usually the source branch (PR branch)
            main_parent_id = parents[0]['id']
            pr_branch_parent_id = parents[1]['id']
            
            # Find all commits that are in the PR branch but not in the target branch
            branch_commits = find_branch_commits(base_url, headers, workspace, repo_slug, 
                                               pr_branch_parent_id, main_parent_id)
            
            # Filter commits that are within our date range
            for commit_id in branch_commits:
                # Skip if already processed
                if commit_id in processed_commits:
                    continue
                    
                # Get commit details
                commit_details = get_commit_details(base_url, headers, workspace, repo_slug, commit_id)
                if commit_details:
                    commit_date = datetime.datetime.fromtimestamp(commit_details.get('authorTimestamp', 0)/1000)
                    if start_date <= commit_date <= end_date:
                        # Get commit stats
                        stats = get_commit_stats(base_url, headers, workspace, repo_slug, commit_id)
                        
                        # Add to PR's associated commits
                        pr['associated_commits'].append({
                            'id': commit_id,
                            'author_name': commit_details.get('author', {}).get('displayName', 'Unknown'),
                            'author_email': commit_details.get('author', {}).get('emailAddress', 'Unknown'),
                            'date': commit_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': commit_details.get('message', ''),
                            'stats': stats
                        })
                        
                        # Update PR totals
                        pr['total_additions'] += stats.get('additions', 0)
                        pr['total_deletions'] += stats.get('deletions', 0)
                        
                        # Mark as processed
                        processed_commits.add(commit_id)
    
    # Step 5: Process the direct commits (those not associated with any PR)
    author_stats = {}  # Will store direct commit stats by author
    direct_commits_by_date = {}  # Will store direct commits grouped by date and author
    
    for commit in direct_commits:
        commit_id = commit['id']
        
        # Skip if already processed as part of a PR
        if commit_id in processed_commits:
            continue
            
        # Get commit details
        commit_date = datetime.datetime.fromtimestamp(commit.get('authorTimestamp', 0)/1000)
        date_str = commit_date.strftime('%Y-%m-%d')
        
        # Get commit stats
        stats = get_commit_stats(base_url, headers, workspace, repo_slug, commit_id)
        author = commit.get('author', {})
        author_name = author.get('displayName', 'Unknown')
        author_email = author.get('emailAddress', 'Unknown')
        
        # Initialize author stats if needed
        if author_name not in author_stats:
            author_stats[author_name] = {
                'email': author_email,
                'additions': 0,
                'deletions': 0,
                'commits': 0,
                'prs': 0,
                'direct_commits': []
            }
            
        # Update stats
        author_stats[author_name]['additions'] += stats.get('additions', 0)
        author_stats[author_name]['deletions'] += stats.get('deletions', 0)
        author_stats[author_name]['commits'] += 1
        
        # Add commit details
        author_stats[author_name]['direct_commits'].append({
            'id': commit_id,
            'date': date_str,
            'message': commit.get('message', ''),
            'additions': stats.get('additions', 0),
            'deletions': stats.get('deletions', 0)
        })
        
        # Group by date
        if date_str not in direct_commits_by_date:
            direct_commits_by_date[date_str] = {}
        
        if author_name not in direct_commits_by_date[date_str]:
            direct_commits_by_date[date_str][author_name] = {
                'additions': 0, 
                'deletions': 0,
                'commits': []
            }
            
        direct_commits_by_date[date_str][author_name]['additions'] += stats.get('additions', 0)
        direct_commits_by_date[date_str][author_name]['deletions'] += stats.get('deletions', 0)
        direct_commits_by_date[date_str][author_name]['commits'].append({
            'id': commit_id[:10],
            'message': commit.get('message', '').split('\n')[0][:40],
            'additions': stats.get('additions', 0),
            'deletions': stats.get('deletions', 0)
        })
        
        # Mark as processed
        processed_commits.add(commit_id)
    
    # Step 6: Compile PR author stats
    for pr in prs:
        author_name = pr['author_name']
        
        if author_name not in author_stats:
            author_stats[author_name] = {
                'email': pr['author_email'],
                'additions': 0,
                'deletions': 0,
                'commits': 0,
                'prs': 0,
                'direct_commits': []
            }
        else:
            if 'prs' not in author_stats[author_name]:
                author_stats[author_name]['prs'] = 0
        
        # Count the PR
        author_stats[author_name]['prs'] += 1
        
        # Add the changes
        author_stats[author_name]['additions'] += pr['total_additions']
        author_stats[author_name]['deletions'] += pr['total_deletions']
        
        # Count the PR commit itself
        author_stats[author_name]['commits'] += 1
        
        # Count associated commits if they have the same author
        for associated_commit in pr['associated_commits']:
            if associated_commit['author_name'] == author_name:
                author_stats[author_name]['commits'] += 1
    
    # Step 7: Load the standard LOC analysis data for comparison
    standard_analysis = None
    try:
        standard_analysis = pd.read_csv('GVT_cx-switch-health-read-assist_user_stats.csv')
    except:
        print("Could not find standard LOC analysis data")
    
    # Output PR results
    print("\nPull Requests in the last 14 days:")
    print("====================================")
    
    # Export PR data to CSV
    with open('all_prs_last_14days.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['PR Number', 'Title', 'Author', 'Date', 'Additions', 'Deletions', 'Total Changes'])
        
        for pr in prs:
            pr_date = datetime.datetime.fromtimestamp(pr['commit'].get('authorTimestamp', 0)/1000)
            print(f"PR #{pr['pr_number']}: {pr['pr_title']}")
            print(f"  Author: {pr['author_name']}")
            print(f"  Date: {pr_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Additions: {pr['total_additions']}, Deletions: {pr['total_deletions']}, Total: {pr['total_additions'] + pr['total_deletions']}")
            
            csv_writer.writerow([
                pr['pr_number'],
                pr['pr_title'],
                pr['author_name'],
                pr_date.strftime('%Y-%m-%d %H:%M:%S'),
                pr['total_additions'],
                pr['total_deletions'],
                pr['total_additions'] + pr['total_deletions']
            ])
    
    print(f"\nPR data exported to all_prs_last_14days.csv")
    
    # Output direct commits by date
    print("\nDirect Commits by Date:")
    print("=====================")
    
    with open('direct_commits_by_date.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Date', 'Author', 'Commits', 'Additions', 'Deletions', 'Total'])
        
        for date_str, authors in sorted(direct_commits_by_date.items()):
            print(f"\nDate: {date_str}")
            for author_name, stats in sorted(authors.items()):
                print(f"  {author_name}: +{stats['additions']}, -{stats['deletions']}, {len(stats['commits'])} commits")
                
                for commit in stats['commits']:
                    print(f"    {commit['id']}: {commit['message']} (+{commit['additions']}, -{commit['deletions']})")
                
                csv_writer.writerow([
                    date_str,
                    author_name,
                    len(stats['commits']),
                    stats['additions'],
                    stats['deletions'],
                    stats['additions'] + stats['deletions']
                ])
    
    print(f"\nDirect commits exported to direct_commits_by_date.csv")
    
    # Output combined stats (PRs + direct commits)
    print("\nCombined Author Statistics (PRs + Direct Commits):")
    print("===============================================")
    
    with open('combined_author_stats.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Author', 'Email', 'PRs', 'Direct Commits', 'Total Commits', 'Additions', 'Deletions', 'Total Changes'])
        
        for author_name, stats in sorted(author_stats.items(), key=lambda x: x[0].lower()):
            prs_count = stats.get('prs', 0)
            direct_commits_count = len(stats.get('direct_commits', []))
            total_commits = stats['commits']
            total_changes = stats['additions'] + stats['deletions']
            
            print(f"{author_name} ({stats['email']}):")
            print(f"  PRs: {prs_count}, Direct Commits: {direct_commits_count}, Total Commits: {total_commits}")
            print(f"  Additions: {stats['additions']}, Deletions: {stats['deletions']}, Total: {total_changes}")
            
            csv_writer.writerow([
                author_name,
                stats['email'],
                prs_count,
                direct_commits_count,
                total_commits,
                stats['additions'],
                stats['deletions'],
                total_changes
            ])
    
    print(f"\nCombined author stats exported to combined_author_stats.csv")
    
    # If we have standard analysis data, compare it with our results
    if standard_analysis is not None:
        print("\nComparison with Standard LOC Analysis:")
        print("====================================")
        
        # Compare the stats for each author
        for _, row in standard_analysis.iterrows():
            author_name = row['name']
            std_additions = row['additions']
            std_deletions = row['deletions']
            std_total = row['total_changes']
            
            if author_name in author_stats:
                our_additions = author_stats[author_name]['additions']
                our_deletions = author_stats[author_name]['deletions']
                our_total = our_additions + our_deletions
                
                print(f"{author_name}:")
                print(f"  Standard Analysis: +{std_additions}, -{std_deletions}, total: {std_total}")
                print(f"  Our Analysis:      +{our_additions}, -{our_deletions}, total: {our_total}")
                
                if std_total != our_total:
                    print(f"  DISCREPANCY DETECTED: {std_total - our_total} lines difference")
                    
                    # Show details for author's direct commits to help diagnose the issue
                    if 'direct_commits' in author_stats[author_name] and author_stats[author_name]['direct_commits']:
                        print(f"  Direct commits for {author_name}:")
                        for commit in author_stats[author_name]['direct_commits']:
                            print(f"    {commit['date']} | {commit['id']} | +{commit['additions']}, -{commit['deletions']} | {commit['message'][:60]}")

def extract_pr_info(commit_message):
    """Extract PR number and title from commit message"""
    # Different patterns to match PR information in commit messages
    patterns = [
        r'Merge pull request #(\d+).*?from.*?\n\n(.*?)(?:\n|$)',
        r'Merged in .*? \(pull request #(\d+)\)\n\n(.*?)(?:\n|$)',
        r'PR #(\d+)[:,] (.*?)(?:\n|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, commit_message, re.DOTALL)
        if match:
            return {
                'number': match.group(1),
                'title': match.group(2).strip()
            }
    
    return None

def get_all_commits(base_url, headers, workspace, repo_slug, start_date, end_date):
    """Get all commits within the date range"""
    api_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
    
    params = {
        'limit': 100,
        'until': end_date.strftime('%Y-%m-%d'),
        'since': start_date.strftime('%Y-%m-%d')
    }
    
    all_commits = []
    
    while True:
        response = requests.get(api_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching commits: {response.status_code}")
            print(response.text)
            return []
        
        data = response.json()
        all_commits.extend(data.get('values', []))
        
        # Check if there are more pages
        is_last_page = data.get('isLastPage', True)
        if is_last_page:
            break
            
        # Update the start parameter for the next page
        params['start'] = data.get('nextPageStart')
        
    return all_commits

def get_commit_stats(base_url, headers, workspace, repo_slug, commit_id):
    """Get additions and deletions for a specific commit"""
    api_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}"
    
    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching commit stats for {commit_id}: {response.status_code}")
        return {'additions': 0, 'deletions': 0}
    
    # Try to get the changes directly from this endpoint
    data = response.json()
    
    # Fallback to the changes endpoint for Bitbucket Server
    changes_url = f"{api_url}/changes"
    response = requests.get(changes_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching commit changes for {commit_id}: {response.status_code}")
        return {'additions': 0, 'deletions': 0}
    
    changes_data = response.json()
    
    additions = 0
    deletions = 0
    
    # Parse the changes data
    for change in changes_data.get('values', []):
        # Calculate additions and deletions based on change type
        if change.get('type') == 'ADD':
            # For added files, all lines are additions
            additions += change.get('additions', 0)
        elif change.get('type') == 'DELETE':
            # For deleted files, all lines are deletions
            deletions += change.get('deletions', 0)
        else:
            # For modified files, count both additions and deletions
            additions += change.get('additions', 0)
            deletions += change.get('deletions', 0)
    
    return {
        'additions': additions,
        'deletions': deletions
    }

def get_commit_details(base_url, headers, workspace, repo_slug, commit_id):
    """Get detailed information for a specific commit"""
    api_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}"
    
    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching commit details for {commit_id}: {response.status_code}")
        return None
    
    return response.json()

def find_branch_commits(base_url, headers, workspace, repo_slug, from_commit, to_commit):
    """Find all commits that are in from_commit's history but not in to_commit's history"""
    # This is a simplified approach - ideally we would use the Bitbucket API's compare endpoint
    # But we'll use a workaround by getting the commit history of both branches
    
    # Get the commits from the source branch (PR branch)
    api_url = f"{base_url}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
    params = {
        'until': from_commit,
        'limit': 100
    }
    
    source_commits = []
    
    while True:
        response = requests.get(api_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching source branch commits: {response.status_code}")
            return []
        
        data = response.json()
        source_commits.extend([commit['id'] for commit in data.get('values', [])])
        
        # Check if there are more pages
        is_last_page = data.get('isLastPage', True)
        if is_last_page:
            break
            
        # Update the start parameter for the next page
        params['start'] = data.get('nextPageStart')
    
    # Get the commits from the target branch (main)
    params = {
        'until': to_commit,
        'limit': 100
    }
    
    target_commits = set()
    
    while True:
        response = requests.get(api_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching target branch commits: {response.status_code}")
            return []
        
        data = response.json()
        target_commits.update([commit['id'] for commit in data.get('values', [])])
        
        # Check if there are more pages
        is_last_page = data.get('isLastPage', True)
        if is_last_page:
            break
            
        # Update the start parameter for the next page
        params['start'] = data.get('nextPageStart')
    
    # Find commits that are in the source branch but not in the target branch
    branch_commits = [commit_id for commit_id in source_commits if commit_id not in target_commits]
    
    return branch_commits

if __name__ == "__main__":
    main()
EOF

# Make the script executable
chmod +x analyze_all_contributions.py

# Run the Bitbucket LOC analyzer with date filtering for the last 14 days
echo "Running standard LOC analysis for the last 14 days..."
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist \
  --token "$(cat ~/.bitbucket_token)" \
  --base-url https://stash.arubanetworks.com \
  --start-date $START_DATE \
  --end-date $END_DATE \
  --group-by day \
  --by-user \
  --export last_14days_member_contributions.csv

# Run our comprehensive analysis
echo -e "\nRunning comprehensive analysis (PRs + Direct Commits)..."
python analyze_all_contributions.py "$START_DATE" "$END_DATE"

# Display a summary of the analyses
echo
echo "======================= FINAL RESULTS ======================="
echo "Standard LOC analysis results:"
echo "  - CSV: last_14days_member_contributions.csv"
echo "  - PNG: GVT_cx-switch-health-read-assist_loc_changes.png"
echo "  - User stats: GVT_cx-switch-health-read-assist_user_stats.csv"
echo
echo "Comprehensive analysis results:"
echo "  - All PRs: all_prs_last_14days.csv"
echo "  - Direct commits: direct_commits_by_date.csv"
echo "  - Combined stats: combined_author_stats.csv"
echo
echo "NOTE: The comprehensive analysis accounts for both PR-based changes"
echo "and direct commits, providing a complete picture of contributions."
echo "============================================================"
