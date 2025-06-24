#!/usr/bin/env python3
"""
Modified version of Bitbucket LOC Analyzer for handling Stash API quirks

This version uses the Bitbucket Server diff endpoint to calculate line changes
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

def get_commit_diff(commit_hash, commit_index=None):
    """
    Get the raw diff for a specific commit and count line changes
    """
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # We need to get the parent commit to create a diff
    url = f"{BASE_URL}/rest/api/1.0/projects/{PROJECT}/repos/{REPO}/commits/{commit_hash}"
    
    try:
        if commit_index is not None and commit_index < 5:
            print(f"Getting diff for commit {commit_hash[:8]}...")
            
        # First, get the commit details to find its parent
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        commit_data = response.json()
        
        # Skip merge commits that have more than one parent
        if len(commit_data.get('parents', [])) > 1:
            if commit_index is not None and commit_index < 5:
                print(f"Skipping merge commit {commit_hash[:8]} (has multiple parents)")
            return 0, 0
        
        # Get the parent commit hash
        parent_hash = commit_data.get('parents', [{}])[0].get('id', None)
        if not parent_hash:
            # This is the initial commit, no parent
            if commit_index is not None and commit_index < 5:
                print(f"Initial commit {commit_hash[:8]}, calculating additions only")
                
            # For the initial commit, we'll just count all lines as additions
            # Get all files in the commit
            changes_url = f"{BASE_URL}/rest/api/1.0/projects/{PROJECT}/repos/{REPO}/commits/{commit_hash}/changes"
            changes_response = requests.get(changes_url, headers=headers)
            changes_response.raise_for_status()
            changes_data = changes_response.json()
            
            additions = 0
            for file_change in changes_data.get('values', []):
                if file_change.get('type') == 'ADD':
                    # For added files, get the file content
                    file_path = file_change.get('path', {}).get('toString', '')
                    content_id = file_change.get('contentId')
                    
                    if content_id:
                        raw_url = f"{BASE_URL}/rest/api/1.0/projects/{PROJECT}/repos/{REPO}/raw/{file_path}?at={commit_hash}"
                        raw_response = requests.get(raw_url, headers=headers)
                        if raw_response.status_code == 200:
                            # Count non-empty lines
                            additions += len([line for line in raw_response.text.splitlines() if line.strip()])
            
            if commit_index is not None and commit_index < 5:
                print(f"Commit {commit_hash[:8]}: +{additions}, -0 (initial commit)")
            
            return additions, 0
        
        # Now get the diff between this commit and its parent
        diff_url = f"{BASE_URL}/rest/api/1.0/projects/{PROJECT}/repos/{REPO}/commits/{commit_hash}/diff"
        diff_response = requests.get(diff_url, headers=headers)
        diff_response.raise_for_status()
        diff_data = diff_response.json()
        
        # Process each file's diff
        additions = 0
        deletions = 0
        
        for diff in diff_data.get('diffs', []):
            # Get the raw diff text
            diff_text = diff.get('text', '')
            
            # Parse the diff to count additions and deletions
            for line in diff_text.splitlines():
                if line.startswith('+') and not line.startswith('+++'):
                    additions += 1
                elif line.startswith('-') and not line.startswith('---'):
                    deletions += 1
        
        if commit_index is not None and commit_index < 5:
            print(f"Commit {commit_hash[:8]}: +{additions}, -{deletions}")
            
        return additions, deletions
            
    except Exception as e:
        print(f"Error getting diff for commit {commit_hash}: {e}")
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
        
        # Get stats for this commit
        additions, deletions = get_commit_diff(commit_hash, i)
        
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
    
    if len(df_grouped) > 0:
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
