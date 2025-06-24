#!/usr/bin/env python3
"""
Modified version of Bitbucket LOC Analyzer for handling Stash API quirks
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import json
import os
from dateutil.parser import parse
import sys

# Replace these with your values
TOKEN = "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V"
BASE_URL = "https://stash.arubanetworks.com"
PROJECT = "GVT"
REPO = "cx-switch-health-read-assist"
JSON_FILE = "cx_commits.json"
OUTPUT_CSV = "cx_switch_health_loc.csv"
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

def fetch_commits():
    """Fetch commits directly using the token"""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    url = f"{BASE_URL}/rest/api/1.0/projects/{PROJECT}/repos/{REPO}/commits"
    params = {"limit": 100}
    
    print(f"Fetching commits from {url}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()['values']
    except Exception as e:
        print(f"Error fetching commits: {e}")
        return []

def get_commit_changes(commit_hash, commit_index=None):
    """Get the additions and deletions for a specific commit"""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    url = f"{BASE_URL}/rest/api/1.0/projects/{PROJECT}/repos/{REPO}/commits/{commit_hash}/changes"
    
    try:
        if commit_index is not None and commit_index < 5:
            print(f"Getting changes for commit {commit_hash[:8]}...")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Debug output
        if commit_index == 0:  # For the first commit only
            print(f"Response structure: {json.dumps(data, indent=2)[:500]}...")
        
        additions = 0
        deletions = 0
        
        for file in data.get('values', []):
            file_path = file.get('path', {}).get('toString', '')
            
            # Debug for first commit
            if commit_index == 0 and additions == 0 and deletions == 0:
                print(f"File data: {json.dumps(file, indent=2)}")
            
            # Try to get additions and deletions
            if file.get('type') == 'ADD':
                # New file, count all lines as additions
                adds = file.get('additions', 0) 
                if adds == 0:
                    adds = file.get('size', 0)
                additions += adds
                if commit_index == 0:
                    print(f"ADD: +{adds} for {file_path}")
            elif file.get('type') == 'DELETE':
                # Deleted file, count all lines as deletions
                dels = file.get('deletions', 0)
                if dels == 0:
                    dels = file.get('size', 0)
                deletions += dels
                if commit_index == 0:
                    print(f"DELETE: -{dels} for {file_path}")
            elif file.get('type') == 'MODIFY':
                # Modified file
                adds = file.get('additions', 0)
                dels = file.get('deletions', 0)
                if adds == 0 and dels == 0:
                    # If no specific counts, estimate based on content changes
                    line_changes = file.get('size', 0) / 2
                    additions += line_changes
                    deletions += line_changes
                    if commit_index == 0:
                        print(f"MODIFY (est): +{line_changes}, -{line_changes} for {file_path}")
                else:
                    additions += adds
                    deletions += dels
                    if commit_index == 0:
                        print(f"MODIFY: +{adds}, -{dels} for {file_path}")
        
        if commit_index is not None and commit_index < 5:  # For the first 5 commits
            print(f"Commit {commit_hash[:8]}: +{additions}, -{deletions}")
            
        return additions, deletions
    except Exception as e:
        print(f"Error fetching changes for commit {commit_hash}: {e}")
        # Print full exception for debugging
        import traceback
        traceback.print_exc()
        return 0, 0

def main():
    print(f"Analyzing {PROJECT}/{REPO}")
    
    # Try to load commits from JSON file first
    if os.path.exists(JSON_FILE):
        print(f"Loading commits from {JSON_FILE}...")
        commits = load_commits_from_json(JSON_FILE)
    else:
        print("JSON file not found, fetching commits from API...")
        commits = fetch_commits()
    
    if not commits:
        print("No commits found.")
        sys.exit(1)
    
    print(f"Processing {len(commits)} commits...")
    
    # Process commit data
    data = []
    for i, commit in enumerate(commits):
        commit_hash = commit['id']
        # Extract date from authorTimestamp (Unix epoch milliseconds)
        timestamp_ms = commit.get('authorTimestamp', 0)
        commit_date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
        
        # Skip merge commits if desired
        if commit.get('message', '').startswith('Merge '):
            continue
        
        # Get stats for this commit
        additions, deletions = get_commit_changes(commit_hash, i)
        
        data.append({
            'date': commit_date,
            'additions': additions,
            'deletions': deletions
        })
        
        # Print progress every 10 commits
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(commits)} commits")
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Group by chosen time period
    if GROUP_BY == 'day':
        df_grouped = df.groupby(df['date'].dt.date).sum()
    elif GROUP_BY == 'week':
        df_grouped = df.groupby(pd.Grouper(key='date', freq='W-MON')).sum()
    else:  # default to month
        df_grouped = df.groupby(pd.Grouper(key='date', freq='M')).sum()
    
    # Export to CSV if requested
    if OUTPUT_CSV:
        df_grouped.to_csv(OUTPUT_CSV)
        print(f"Exported data to {OUTPUT_CSV}")
    
    # Generate plot
    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    df_grouped['additions'].plot(kind='bar', ax=ax, color='green', position=0, width=0.4)
    df_grouped['deletions'].plot(kind='bar', ax=ax, color='red', position=1, width=0.4)
    
    plt.title(f'Lines of Code Changes in {PROJECT}/{REPO}')
    plt.xlabel(f'Time ({GROUP_BY})')
    plt.ylabel('Lines of Code')
    plt.legend(['Additions', 'Deletions'])
    plt.tight_layout()
    
    # Save plot
    plt.savefig('cx_switch_health_loc.png')
    print("Saved chart to cx_switch_health_loc.png")
    
    # Print summary
    total_additions = df_grouped['additions'].sum()
    total_deletions = df_grouped['deletions'].sum()
    print(f"\nSummary:")
    print(f"Total Additions: {int(total_additions)}")
    print(f"Total Deletions: {int(total_deletions)}")
    print(f"Net Change: {int(total_additions - total_deletions)}")
    print(f"Analysis Complete!")

if __name__ == "__main__":
    main()
