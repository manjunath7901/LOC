#!/usr/bin/env python3
"""
Test script to verify the timestamp handling fix in BitbucketLOCAnalyzer
"""

import json
import os
from datetime import datetime, timedelta

# Load commits from JSON file
def load_commits_from_json(file_path="cx_commits.json"):
    """Load commits from a JSON file"""
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

# Test function to compare timestamp handling
def test_timestamp_handling():
    commits = load_commits_from_json()
    if not commits:
        print("No commits found.")
        return
    
    # Define a cutoff date (60 days ago)
    cutoff_date = datetime.now() - timedelta(days=60)
    cutoff_timestamp_ms = int(cutoff_date.timestamp() * 1000)
    
    print(f"\nTesting timestamp handling for commits after {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"Cutoff timestamp: {cutoff_timestamp_ms}\n")
    
    print("Old method (authorTimestamp only):")
    old_method_commits = []
    for commit in commits:
        author_timestamp_ms = commit.get('authorTimestamp', 0)
        if author_timestamp_ms >= cutoff_timestamp_ms:
            old_method_commits.append(commit)
    
    print(f"Found {len(old_method_commits)} commits with old method")
    
    print("\nNew method (max of authorTimestamp and committerTimestamp):")
    new_method_commits = []
    for commit in commits:
        author_timestamp_ms = commit.get('authorTimestamp', 0)
        committer_timestamp_ms = commit.get('committerTimestamp', author_timestamp_ms)
        timestamp_ms = max(author_timestamp_ms, committer_timestamp_ms)
        
        if timestamp_ms >= cutoff_timestamp_ms:
            new_method_commits.append(commit)
    
    print(f"Found {len(new_method_commits)} commits with new method")
    
    # Find commits that would be included with new method but not old method
    additional_commits = []
    for commit in new_method_commits:
        author_timestamp_ms = commit.get('authorTimestamp', 0)
        committer_timestamp_ms = commit.get('committerTimestamp', author_timestamp_ms)
        
        # If authorTimestamp is before cutoff but committerTimestamp is after
        if author_timestamp_ms < cutoff_timestamp_ms and committer_timestamp_ms >= cutoff_timestamp_ms:
            additional_commits.append(commit)
    
    print(f"\nAdditional commits included with new method: {len(additional_commits)}")
    
    if additional_commits:
        print("\nDetails of additional commits:")
        for commit in additional_commits:
            author_time = datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000)
            committer_time = datetime.fromtimestamp(commit.get('committerTimestamp', 0) / 1000)
            message_first_line = commit.get('message', '').split('\n')[0][:50] + "..."
            print(f"Commit {commit['id'][:8]}")
            print(f"  Author: {commit.get('author', {}).get('displayName', 'Unknown')}")
            print(f"  Author timestamp: {author_time}")
            print(f"  Committer timestamp: {committer_time}")
            print(f"  Message: {message_first_line}")
            print()

if __name__ == "__main__":
    test_timestamp_handling()
