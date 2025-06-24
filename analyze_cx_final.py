#!/usr/bin/env python3
"""
Final version of Bitbucket LOC Analyzer that correctly parses diff output
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import json
import os
import re
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

def process_commit_diff(commit_hash, commit_index=None):
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
        
        # Skip merge commits (has more than one parent)
        if len(commit_data.get('parents', [])) > 1:
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

def main():
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
    
    print(f"Processing {len(commits)} commits...")
    
    # Process commit data
    data = []
    for i, commit in enumerate(commits):
        commit_hash = commit['id']
        # Use the later timestamp between author and committer
        author_timestamp_ms = commit.get('authorTimestamp', 0)
        committer_timestamp_ms = commit.get('committerTimestamp', author_timestamp_ms)
        timestamp_ms = max(author_timestamp_ms, committer_timestamp_ms)
        commit_date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
        
        # Get stats for this commit (skip merge commits)
        additions, deletions = process_commit_diff(commit_hash, i)
        
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
        df_grouped = df.groupby(pd.Grouper(key='date', freq='ME')).sum()
    
    # Export to CSV if requested
    if OUTPUT_CSV:
        df_grouped.to_csv(OUTPUT_CSV)
        print(f"Exported data to {OUTPUT_CSV}")
    
    # Generate plot
    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    
    if not df_grouped.empty:
        df_grouped['additions'].plot(kind='bar', ax=ax, color='green', position=0, width=0.4)
        df_grouped['deletions'].plot(kind='bar', ax=ax, color='red', position=1, width=0.4)
        
        # Get summary statistics
        total_additions = df_grouped['additions'].sum()
        total_deletions = df_grouped['deletions'].sum()
        
        plt.title(f'Lines of Code Changes in {PROJECT}/{REPO}')
        plt.xlabel(f'Time ({GROUP_BY})')
        plt.ylabel('Lines of Code')
        plt.legend(['Additions', 'Deletions'])
        plt.tight_layout()
        
        # Save plot
        plt.savefig('cx_switch_health_loc.png')
        print("Saved chart to cx_switch_health_loc.png")
        
        # Print summary
        print(f"\nSummary:")
        print(f"Total Additions: {int(total_additions)}")
        print(f"Total Deletions: {int(total_deletions)}")
        print(f"Net Change: {int(total_additions - total_deletions)}")
    else:
        print("No data available for plotting.")
        
    print(f"Analysis Complete!")

if __name__ == "__main__":
    main()
