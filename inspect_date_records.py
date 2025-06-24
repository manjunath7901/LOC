#!/usr/bin/env python3
import requests
import json
import sys
import datetime
import os
from datetime import datetime, timedelta

# Configuration
token_file = "~/.bitbucket_token"
try:
    with open(token_file.replace("~", "/Users/kallatti"), 'r') as f:
        token = f.read().strip()
except:
    token = "BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V"

base_url = "https://stash.arubanetworks.com"
api_base = base_url
workspace = "GVT"
repo_slug = "cx-switch-health-read-assist"
headers = {"Authorization": f"Bearer {token}"}

# Get all commits within a much larger window
end_date = datetime.now()
start_date = end_date - timedelta(days=30)  # Look further back
start_timestamp = int(start_date.timestamp() * 1000)
end_timestamp = int(end_date.timestamp() * 1000)

print(f"Searching for commits between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")

# Get all commits 
url = f"{api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
params = {
    'limit': 500,  # Get more commits
    'start': 0
}

all_commits = []
while True:
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        sys.exit(1)
    
    data = response.json()
    commits = data.get('values', [])
    
    for commit in commits:
        timestamp = commit.get('authorTimestamp', 0)
        if start_timestamp <= timestamp <= end_timestamp:
            all_commits.append(commit)
            
    is_last_page = data.get('isLastPage', True)
    if is_last_page:
        break
    
    params['start'] = data.get('nextPageStart')

print(f"Found {len(all_commits)} commits in the date range")

# Create a CSV file with dates and LOC changes
with open("detailed_commits.csv", "w") as f:
    f.write("date,commit_id,author,message,additions,deletions,total_changes\n")
    
    for commit in all_commits:
        commit_id = commit.get('id')
        author_name = commit.get('author', {}).get('displayName', 'Unknown')
        commit_date = datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000)
        date_str = commit_date.strftime('%Y-%m-%d')
        message = commit.get('message', '').split('\n')[0]  # First line only
        
        # Get the commit diff to calculate additions and deletions
        diff_url = f"{api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_id}/diff"
        diff_response = requests.get(diff_url, headers=headers)
        
        additions = 0
        deletions = 0
        
        if diff_response.status_code == 200:
            diff_data = diff_response.json()
            for diff_file in diff_data.get('diffs', []):
                for hunk in diff_file.get('hunks', []):
                    for segment in hunk.get('segments', []):
                        if segment.get('type') == 'ADDED':
                            additions += len(segment.get('lines', []))
                        elif segment.get('type') == 'REMOVED':
                            deletions += len(segment.get('lines', []))
        
        total_changes = additions + deletions
        
        # Clean message for CSV
        message = message.replace('"', '""')
        
        f.write(f'"{date_str}","{commit_id[:8]}","{author_name}","{message}",{additions},{deletions},{total_changes}\n')

print(f"Created detailed_commits.csv with {len(all_commits)} entries")

# Specifically look for June 12 data
print("\n=== ANALYZING JUNE 12 DATA ===")
june12_commits = [c for c in all_commits if datetime.fromtimestamp(c.get('authorTimestamp', 0) / 1000).strftime('%Y-%m-%d') == '2025-06-12']
print(f"Found {len(june12_commits)} commits on June 12, 2025")

# Read standard LOC data 
import pandas as pd
try:
    standard_loc = pd.read_csv('standard_loc_last_14days.csv')
    june12_data = standard_loc[standard_loc['date'] == '2025-06-12']
    
    if not june12_data.empty:
        print("June 12 data from standard_loc_last_14days.csv:")
        print(f"  Additions: {june12_data['additions'].values[0]}")
        print(f"  Deletions: {june12_data['deletions'].values[0]}")
    else:
        print("No June 12 data in standard_loc_last_14days.csv")
except:
    print("Could not read standard_loc_last_14days.csv")

print("\n=== ANALYZING BITBUCKET LOC ANALYZER CODE ===")
# Check how the LOC analyzer gets and processes commit dates
import subprocess
result = subprocess.run(['grep', '-A', '10', 'if start_date and commit_date', '/Users/kallatti/LOC/bitbucket_loc_analyzer.py'], capture_output=True, text=True)
print(result.stdout)

print("\nChecking how date filtering is performed...")
result = subprocess.run(['grep', '-A', '20', 'Filtering commits by date', '/Users/kallatti/LOC/bitbucket_loc_analyzer.py'], capture_output=True, text=True)
print(result.stdout)
