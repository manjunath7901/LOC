#!/usr/bin/env python3
"""
Enhanced version of Bitbucket LOC Analyzer that analyzes commits by specific user
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import os
import re
import argparse
from dateutil.parser import parse
import sys

# Default values
TOKEN = "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V"
BASE_URL = "https://stash.arubanetworks.com"
PROJECT = "GVT"
REPO = "cx-switch-health-read-assist"
JSON_FILE = "cx_commits.json"
GROUP_BY = "month"  # 'day', 'week', or 'month'

def load_commits_from_json(file_path):
    """Load commits from a JSON file (fetched using fetch_cx_commits.sh)"""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            if 'values' in data:
                return data['values']
            else:
                return []
    else:
        print(f"Error: JSON file {file_path} not found.")
        return []

def process_commit_diff(commit_hash, commit_index=None, include_merges=False):
    """
    Process the diff of a commit to count line additions and deletions
    """
    headers = {"Authorization": f"Bearer {TOKEN}"}
    url = f"{BASE_URL}/rest/api/1.0/projects/{PROJECT}/repos/{REPO}/commits/{commit_hash}"
    
    try:
        # First get the commit info to check if it's a merge commit
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        commit_data = response.json()
        
        # Skip merge commits (has more than one parent) unless include_merges is True
        if len(commit_data.get('parents', [])) > 1 and not include_merges:
            if commit_index is not None and commit_index < 5:
                print(f"Skipping merge commit {commit_hash[:8]} (has {len(commit_data.get('parents', []))} parents)")
            return 0, 0
            
        # Now get the diff
        diff_url = f"{BASE_URL}/rest/api/1.0/projects/{PROJECT}/repos/{REPO}/commits/{commit_hash}/diff"
        if commit_index is not None and commit_index < 5:
            print(f"Getting diff for non-merge commit {commit_hash[:8]}...")
            
        diff_response = requests.get(diff_url, headers=headers)
        diff_response.raise_for_status()
        diff_data = diff_response.json()
        
        total_additions = 0
        total_deletions = 0
        
        # Process each file's hunks
        for diff_file in diff_data.get('diffs', []):
            for hunk in diff_file.get('hunks', []):
                for segment in hunk.get('segments', []):
                    if segment.get('type') == 'ADDED':
                        total_additions += len(segment.get('lines', []))
                    elif segment.get('type') == 'REMOVED':
                        total_deletions += len(segment.get('lines', []))
                        
        if commit_index is not None and commit_index < 5:
            print(f"Lines changed in {commit_hash[:8]}: +{total_additions}, -{total_deletions}")
            
        return total_additions, total_deletions
    except Exception as e:
        print(f"Error processing diff for {commit_hash[:8]}: {e}")
        return 0, 0

def extract_author_info(commit):
    """Extract author information from a commit"""
    author = commit.get('author', {})
    # Try to get email from emailAddress field
    email = author.get('emailAddress', '')
    # If emailAddress is missing, try the name field which might contain email
    if '@' not in email and '@' in author.get('name', ''):
        email = author.get('name', '')
        
    # Get display name or fallback to name or email
    name = author.get('displayName', author.get('name', email))
    
    return {
        'name': name,
        'email': email,
        'username': author.get('slug', '')
    }

def main():
    parser = argparse.ArgumentParser(description='Analyze LOC changes by a specific user and time range')
    parser.add_argument('--user', type=str, help='User to filter by (name, email, or username)')
    parser.add_argument('--email-domain', type=str, help='Filter users by email domain (e.g., "@example.com")')
    parser.add_argument('--output', type=str, help='Output CSV filename', default='user_loc_stats.csv')
    parser.add_argument('--show-all-users', action='store_true', help='Show stats for all users')
    parser.add_argument('--days', type=int, help='Analyze commits from the last N days (e.g., 30, 60, 90)')
    parser.add_argument('--since', type=str, help='Analyze commits since this date (YYYY-MM-DD)')
    parser.add_argument('--until', type=str, help='Analyze commits until this date (YYYY-MM-DD)')
    parser.add_argument('--include-merges', action='store_true', help='Include merge commits in the analysis')
    args = parser.parse_args()
    
    print(f"Analyzing {PROJECT}/{REPO}")
    
    # Try to load commits from JSON file first
    if os.path.exists(JSON_FILE):
        print(f"Loading commits from {JSON_FILE}...")
        commits = load_commits_from_json(JSON_FILE)
    else:
        print("JSON file not found. Please run fetch_cx_commits.sh first.")
        sys.exit(1)
    
    if not commits:
        print("No commits found.")
        sys.exit(1)
    
    # Calculate date filters
    current_date = datetime.now()
    since_date = None
    until_date = None
    
    if args.days:
        since_date = current_date - timedelta(days=args.days)
        print(f"Filtering commits from the last {args.days} days (since {since_date.strftime('%Y-%m-%d')})")
    elif args.since:
        try:
            since_date = datetime.strptime(args.since, '%Y-%m-%d')
            print(f"Filtering commits since {args.since}")
        except ValueError:
            print(f"Error: Invalid date format for --since. Use YYYY-MM-DD.")
            sys.exit(1)
    
    if args.until:
        try:
            until_date = datetime.strptime(args.until, '%Y-%m-%d')
            print(f"Filtering commits until {args.until}")
        except ValueError:
            print(f"Error: Invalid date format for --until. Use YYYY-MM-DD.")
            sys.exit(1)
            
    # Before processing, if we're showing all users, just print the list and exit
    if args.show_all_users:
        all_authors = {}
        filtered_commits = []
        
        # Filter commits by date if specified
        for commit in commits:
            # Use the later timestamp between author and committer
            author_timestamp_ms = commit.get('authorTimestamp', 0)
            committer_timestamp_ms = commit.get('committerTimestamp', 0)
            timestamp_ms = max(author_timestamp_ms, committer_timestamp_ms)
            commit_date = datetime.fromtimestamp(timestamp_ms / 1000)
            
            # Apply date filters if specified
            if (since_date and commit_date < since_date) or (until_date and commit_date > until_date):
                continue
                
            filtered_commits.append(commit)
            author_info = extract_author_info(commit)
            key = author_info['email'].lower()
            if key not in all_authors:
                all_authors[key] = author_info
        
        print("\nUsers who have committed to this repository:")
        print("--------------------------------------------")
        for idx, (_, author) in enumerate(sorted(all_authors.items(), key=lambda x: x[1]['name'])):
            print(f"{idx+1}. {author['name']} ({author['email']})")
        print(f"\nTotal: {len(all_authors)} unique users in the specified time range")
        print(f"Commits analyzed: {len(filtered_commits)} out of {len(commits)} total commits")
        return
    
    # Filter commits by date if specified
    filtered_commits = []
    for commit in commits:
        # Use the later timestamp between author and committer
        author_timestamp_ms = commit.get('authorTimestamp', 0)
        committer_timestamp_ms = commit.get('committerTimestamp', 0)
        timestamp_ms = max(author_timestamp_ms, committer_timestamp_ms)
        commit_date = datetime.fromtimestamp(timestamp_ms / 1000)
        
        # Apply date filters if specified
        if (since_date and commit_date < since_date) or (until_date and commit_date > until_date):
            continue
            
        filtered_commits.append(commit)
    
    print(f"Processing {len(filtered_commits)} commits out of {len(commits)} total")
    
    # Process commit data
    user_data = {}
    all_data = []
    
    for i, commit in enumerate(filtered_commits):
        commit_hash = commit['id']
        # Extract date using the later of author and committer timestamps 
        author_timestamp_ms = commit.get('authorTimestamp', 0)
        committer_timestamp_ms = commit.get('committerTimestamp', author_timestamp_ms)
        timestamp_ms = max(author_timestamp_ms, committer_timestamp_ms)
        commit_date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
        author_info = extract_author_info(commit)
        
        # Filter by specific user if provided
        user_match = False
        if args.user:
            search_term = args.user.lower()
            if (search_term in author_info['name'].lower() or 
                search_term in author_info['email'].lower() or 
                search_term in author_info['username'].lower()):
                user_match = True
        elif args.email_domain:
            domain = args.email_domain.lower()
            if domain in author_info['email'].lower():
                user_match = True
        else:
            # If no filter is specified, include all users
            user_match = True
            
        if user_match:
            # Get stats for this commit
            additions, deletions = process_commit_diff(commit_hash, i, args.include_merges)
            
            # Store by user
            author_key = author_info['email'].lower()
            if author_key not in user_data:
                user_data[author_key] = {
                    'name': author_info['name'],
                    'email': author_info['email'],
                    'commits': 0,
                    'additions': 0,
                    'deletions': 0
                }
            
            user_data[author_key]['commits'] += 1
            user_data[author_key]['additions'] += additions
            user_data[author_key]['deletions'] += deletions
            
            # Store detailed data for time-series analysis
            all_data.append({
                'date': commit_date,
                'author': author_info['name'],
                'email': author_info['email'],
                'additions': additions,
                'deletions': deletions
            })
        
        # Print progress every 10 commits
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(commits)} commits")
    
    # If we have data, create visualizations and output
    if all_data:
        # Convert to DataFrame for time-series analysis
        df = pd.DataFrame(all_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Group by chosen time period
        if GROUP_BY == 'day':
            df_grouped = df.groupby([df['date'].dt.date, 'author']).sum().reset_index()
        elif GROUP_BY == 'week':
            df_grouped = df.groupby([pd.Grouper(key='date', freq='W-MON'), 'author']).sum().reset_index()
        else:  # default to month
            df_grouped = df.groupby([pd.Grouper(key='date', freq='ME'), 'author']).sum().reset_index()
        
        # Save to CSV
        output_file = args.output
        df_grouped.to_csv(output_file, index=False)
        print(f"Exported time-series data to {output_file}")
        
        # Generate per-user summary report
        print("\nUser Statistics:")
        print("--------------")            # Convert the dictionary to a list of dictionaries for DataFrame
        user_stats = []
        for email, stats in user_data.items():
            user_stats.append({
                'name': stats['name'],
                'email': email,
                'commits': stats['commits'],
                'additions': stats['additions'],
                'deletions': stats['deletions'],
                'total_changes': stats['additions'] + stats['deletions'],
                'net_changes': stats['additions'] - stats['deletions']
            })
            
        # Create DataFrame and sort by total changes
        user_df = pd.DataFrame(user_stats)
        if not user_df.empty:
            user_df = user_df.sort_values('total_changes', ascending=False)
            
            # Save user summary
            user_summary_file = 'user_summary_' + output_file
            user_df.to_csv(user_summary_file, index=False)
            print(f"Exported user summary to {user_summary_file}")
            
            # Print top contributors
            print("\nTop Contributors by LOC:")
            for idx, row in user_df.head(10).iterrows():
                print(f"{idx+1}. {row['name']} - {int(row['additions'])} additions, {int(row['deletions'])} deletions, {int(row['total_changes'])} total")
            
            # Generate visualization
            plt.figure(figsize=(12, 6))
            
            # Plot time series for top users (up to 5)
            top_users = user_df.head(5)['name'].tolist()
            for user in top_users:
                # Create a copy to avoid the SettingWithCopyWarning
                user_data = df_grouped[df_grouped['author'] == user].copy()
                if not user_data.empty:
                    # Calculate total changes (additions + deletions)
                    user_data.loc[:, 'total'] = user_data['additions'] + user_data['deletions']
                    plt.plot(user_data['date'], user_data['total'], marker='o', linestyle='-', label=f"{user} (total changes)")
            
            # Add the time range to the title
            time_range = ""
            if args.days:
                time_range = f" (Last {args.days} Days)"
            elif since_date and until_date:
                time_range = f" ({since_date.strftime('%Y-%m-%d')} to {until_date.strftime('%Y-%m-%d')})"
            elif since_date:
                time_range = f" (Since {since_date.strftime('%Y-%m-%d')})"
            elif until_date:
                time_range = f" (Until {until_date.strftime('%Y-%m-%d')})"
                
            plt.title(f'Total Lines of Code Changed by Top Users in {PROJECT}/{REPO}{time_range}')
            plt.xlabel(f'Time ({GROUP_BY})')
            plt.ylabel('Total Lines Changed (Additions + Deletions)')
            plt.legend()
            plt.tight_layout()
            
            # Save plot
            plt.savefig('user_loc_trends.png')
            print("Saved visualization to user_loc_trends.png")
        else:
            print("No data found for the specified user filter.")
    else:
        if args.days:
            print(f"No commits found in the last {args.days} days")
        elif args.since or args.until:
            date_range = ""
            if args.since:
                date_range += f"since {args.since} "
            if args.until:
                date_range += f"until {args.until}"
            print(f"No commits found {date_range}")
        elif args.user:
            print(f"No commits found for user matching '{args.user}'")
        elif args.email_domain:
            print(f"No commits found for users with email domain '{args.email_domain}'")
        else:
            print("No data to analyze.")

if __name__ == "__main__":
    main()
