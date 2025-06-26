#!/usr/bin/env python3
"""
Bitbucket Lines of Code Analyzer

This script analyzes a Bitbucket repository to track lines added and deleted over time.
It uses the Bitbucket API to retrieve commit data, cloc for counting lines of code,
and visualizes the changes.
"""

import argparse
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import json
import subprocess
import tempfile
import shutil
import hashlib
import time
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from tqdm import tqdm


class APICache:
    """Cache for API responses to reduce network calls"""
    def __init__(self, cache_dir=".api_cache", expiry_seconds=3600):
        """Initialize the cache
        
        Args:
            cache_dir (str): Directory to store cache files
            expiry_seconds (int): Seconds until cache entries expire
        """
        self.cache_dir = cache_dir
        self.expiry = expiry_seconds
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, url, params=None):
        """Generate a unique cache key from URL and params
        
        Args:
            url (str): The API URL
            params (dict): Optional query parameters
            
        Returns:
            str: MD5 hash of the URL and parameters
        """
        key_data = f"{url}_{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, url, params=None):
        """Retrieve data from cache if available and not expired
        
        Args:
            url (str): The API URL
            params (dict): Optional query parameters
            
        Returns:
            dict: Cached response data or None if not in cache or expired
        """
        key = self._get_cache_key(url, params)
        cache_file = os.path.join(self.cache_dir, key)
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                try:
                    data = json.load(f)
                    if time.time() - data['timestamp'] < self.expiry:
                        return data['content']
                except (json.JSONDecodeError, KeyError):
                    # Handle corrupted cache files
                    pass
        return None
    
    def set(self, url, params, content):
        """Save API response to cache
        
        Args:
            url (str): The API URL
            params (dict): Optional query parameters
            content (dict): The API response to cache
        """
        key = self._get_cache_key(url, params)
        cache_file = os.path.join(self.cache_dir, key)
        
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'content': content
            }, f)


class BitbucketLOCAnalyzer:
    def __init__(self, base_url=None, token=None):
        """Initialize the analyzer with Bitbucket/Stash credentials.
        
        Args:
            base_url (str): Base URL for self-hosted Bitbucket/Stash instance (e.g. https://stash.example.com)
            token (str): Bitbucket access token for Bearer authentication
        """
        self.headers = {}
        self.auth = None
        self.cache = APICache()  # Initialize API cache
        
        # Set base URL for API (default to Bitbucket Cloud if not specified)
        self.base_url = base_url if base_url else "https://api.bitbucket.org"
        # Remove trailing slash if present
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
        
        # Check if this is a Stash/Bitbucket Server instance
        self.is_stash = "api.bitbucket.org" not in self.base_url
        
        # Prepare API base URLs based on instance type
        if self.is_stash:
            # For Stash/Bitbucket Server
            self.api_base = self.base_url  # Base URL is already the full server URL
        else:
            # For Bitbucket Cloud
            self.api_base = f"{self.base_url}/2.0"  # Add API version for Bitbucket Cloud
        
        if token:
            # Set the Bearer token format consistently for both Stash and Cloud
            if token.startswith('Bearer '):
                self.headers['Authorization'] = token
            else:
                self.headers['Authorization'] = f'Bearer {token}'
            
            print(f"Using Bearer token authentication: {token[:5]}...")
            print(f"Headers: {self.headers}")
        else:
            raise ValueError("A token must be provided for Bearer authentication")
            
    def test_connection(self, workspace=None, repo_slug=None):
        """
        Test the connection to the Bitbucket server and verify authentication.
        
        Args:
            workspace (str, optional): Bitbucket workspace/project key to test
            repo_slug (str, optional): Repository slug to test
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        print("\nTesting connection to Bitbucket server...")
        
        try:
            # Test 1: Basic connectivity to the server
            test_url = self.base_url
            
            # Make a HEAD request to the base URL to check if the server is reachable
            print(f"Testing basic connectivity to {test_url}")
            try:
                response = requests.head(test_url, timeout=10)
                print(f"Server is reachable. Status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Cannot reach server: {e}")
                print("Please check your network connection and the base URL.")
                print(f"DNS resolution for {self.base_url.split('//')[1].split('/')[0]}")
                return False
            
            # Test 2: API endpoint access
            if self.is_stash:
                test_url = f"{self.api_base}/rest/api/1.0/"
            else:
                test_url = f"{self.api_base}/"
            
            print(f"\nTesting API endpoint: {test_url}")
            
            # Make the request using our helper method
            response_json = self._make_request(test_url)
            
            if response_json is None:
                print("Cannot access API endpoint. Authentication may be required.")
            else:
                print("API endpoint is accessible.")
                
            # Test 3: Repository access if workspace and repo_slug are provided
            if workspace and repo_slug:
                if self.is_stash:
                    test_url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}"
                else:
                    test_url = f"{self.api_base}/repositories/{workspace}/{repo_slug}"
                
                print(f"\nTesting repository access: {test_url}")
                
                # Make the request using our helper method
                response_json = self._make_request(test_url)
                
                if response_json is None:
                    print(f"Cannot access repository {workspace}/{repo_slug}.")
                    print("Please check if the repository exists and you have permission to access it.")
                    return False
                else:
                    print(f"Repository {workspace}/{repo_slug} is accessible.")
                    return True
            
            # If we reach here and haven't tested a specific repo, return based on API access
            return response_json is not None
            
        except Exception as e:
            print(f"Error during connection test: {e}")
            return False
    
    def get_commits(self, workspace, repo_slug, start_date=None, end_date=None):
        """
        Get commits for a repository within a specified date range.
        
        Args:
            workspace (str): Bitbucket workspace/project key (for Stash/Server) or username/team (for Cloud)
            repo_slug (str): Repository slug (repository name)
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            list: List of commit data
        """
        all_commits = []
        start = 0  # For Stash/Bitbucket Server
        limit = 100
        page = 1
        pagelen = 100  # For Bitbucket Cloud
        
        # If no end date is provided, use current date
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # If no start date is provided, use date 3 months ago
        if not start_date:
            start_date = (datetime.now() - relativedelta(months=3)).strftime('%Y-%m-%d')
            
        print(f"Analyzing commits from {start_date} to {end_date}")
        
        # Start timestamp in ISO format
        start_timestamp = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%SZ')
        # End timestamp in ISO format
        end_timestamp = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%SZ')
            
        while True:
            # Different APIs for Stash/Server vs Cloud
            if self.is_stash:
                # Stash/Bitbucket Server API
                url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
                params = {
                    'limit': limit,
                    'start': start
                }
                
                # Debug information
                print(f"Using Stash URL: {url}")
                
                # Add date filters if supported
                # For Stash/Bitbucket Server, the date format is different and API behaves differently
                # Many Stash instances don't properly support the 'since' parameter, so we'll handle date filtering ourselves
                if start_date:
                    print(f"Note: For Stash/Bitbucket Server, we'll retrieve all commits and filter by date in memory")
                    # Don't use since parameter as it can cause "Commit does not exist" errors
                    # We'll filter commits post-retrieval
                
                # For Stash, we'll just leave out the date parameters for API
                # This avoids the "Commit does not exist" error
            else:
                # Bitbucket Cloud API
                url = f"{self.api_base}/repositories/{workspace}/{repo_slug}/commits"
                params = {
                    'pagelen': pagelen,
                    'page': page
                }
                
                # Debug information
                print(f"Using Bitbucket Cloud URL: {url}")
                
                # Add date filters
                if start_date:
                    params['since'] = start_timestamp
                
            if end_date:
                # Add end date filter for Bitbucket Cloud
                if not self.is_stash:
                    params['until'] = end_timestamp
            
            # Make the request using our helper method
            response_json = self._make_request(url, params)
            
            if not response_json:
                # If request failed, return empty list
                return []
            
            if self.is_stash:
                # Stash/Bitbucket Server format
                if 'values' not in response_json or not response_json['values']:
                    break
                
                commits = response_json['values']
                all_commits.extend(commits)
                
                # Check if there are more commits
                if response_json.get('isLastPage', True):
                    break
                
                # Update start parameter for next page
                start = response_json.get('nextPageStart', 0)
            else:
                # Bitbucket Cloud format
                if 'values' not in response_json or not response_json['values']:
                    break
                
                commits = response_json['values']
                all_commits.extend(commits)
                
                # Check for next page URL
                if 'next' not in response_json:
                    break
                
                # Get the next page URL
                url = response_json['next']
                # When using a direct URL, we don't need params anymore
                params = {}
            
        # Post-process for date filtering if needed (particularly for Stash/Bitbucket Server)
        if start_date or end_date:
            filtered_commits = []
            start_timestamp_ms = 0
            end_timestamp_ms = float("inf")
            
            # Convert date strings to timestamp in milliseconds if provided
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                start_timestamp_ms = int(start_dt.timestamp() * 1000)
                
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                end_timestamp_ms = int(end_dt.timestamp() * 1000)
            
            print(f"Filtering commits by date: {start_date or 'any'} to {end_date or 'any'}")
            print(f"Total commits before filtering: {len(all_commits)}")
            
            # Filter commits by date
            for commit in all_commits:
                # Use the later timestamp between author and committer
                author_timestamp_ms = commit.get('authorTimestamp', 0)
                committer_timestamp_ms = commit.get('committerTimestamp', author_timestamp_ms)
                timestamp_ms = max(author_timestamp_ms, committer_timestamp_ms)
                
                if start_timestamp_ms <= timestamp_ms <= end_timestamp_ms:
                    filtered_commits.append(commit)
            
            print(f"Total commits after filtering: {len(filtered_commits)}")
            return filtered_commits
        
        return all_commits
    
    def get_commit_stats(self, workspace, repo_slug, commit_hash, file_extensions=None):
        """
        Get statistics for a specific commit.
        
        Args:
            workspace (str): Bitbucket workspace or project key
            repo_slug (str): Repository slug
            commit_hash (str): Commit hash
            file_extensions (list): List of file extensions to include (e.g., ['.py', '.js'])
            
        Returns:
            dict: Dictionary with additions and deletions
        """
        if self.is_stash:
            # First check if it's a merge commit by getting commit info
            url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_hash}"
            commit_info = self._make_request(url)
            
            # Skip merge commits (has more than one parent)
            if commit_info and len(commit_info.get('parents', [])) > 1:
                return {'additions': 0, 'deletions': 0}
            
            # For Stash/Bitbucket Server - get detailed diff information for more accurate counts
            url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_hash}/diff"
        else:
            # For Bitbucket Cloud
            url = f"{self.api_base}/repositories/{workspace}/{repo_slug}/diffstat/{commit_hash}"
        
        # Make the request using our helper method
        response_json = self._make_request(url)
        
        if not response_json:
            # If request failed, return zeros
            return {'additions': 0, 'deletions': 0}
        
        # Calculate additions and deletions from diff statistics
        additions = 0
        deletions = 0
        
        if self.is_stash:
            # Stash/Bitbucket Server format - improved processing
            for diff_file in response_json.get('diffs', []):
                # Check file extension if specified
                source = diff_file.get('source')
                destination = diff_file.get('destination')
                file_path = ''
                
                if source is not None:
                    file_path = source.get('toString', '')
                elif destination is not None:
                    file_path = destination.get('toString', '')
                    
                if file_extensions and not any(file_path.endswith(ext) for ext in file_extensions):
                    continue
                
                # Process each file's hunks
                for hunk in diff_file.get('hunks', []):
                    for segment in hunk.get('segments', []):
                        if segment.get('type') == 'ADDED':
                            additions += len(segment.get('lines', []))
                        elif segment.get('type') == 'REMOVED':
                            deletions += len(segment.get('lines', []))
        else:
            # Bitbucket Cloud format
            for file in response_json.get('values', []):
                # Filter by file extension if specified
                file_path = file.get('new', {}).get('path', '') or file.get('old', {}).get('path', '')
                if file_extensions and not any(file_path.endswith(ext) for ext in file_extensions):
                    continue
                    
                # Add up additions and deletions from each file
                additions += file.get('lines_added', 0)
                deletions += file.get('lines_removed', 0)
        
        return {
            'additions': additions,
            'deletions': deletions
        }
    
    def analyze_repository(self, workspace, repo_slug, start_date=None, end_date=None, group_by='day', 
                          file_extensions=None, ignore_merges=False, include_merges=False, by_user=False, 
                          focus_user=None):
        """
        Analyze repository for lines added and deleted over time.
        
        Args:
            workspace (str): Bitbucket workspace
            repo_slug (str): Repository slug
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            group_by (str): How to group the results ('day', 'week', 'month')
            file_extensions (list): List of file extensions to include (e.g., ['.py', '.js'])
            ignore_merges (bool): If True, ignore merge commits
            include_merges (bool): If True, include merge commits (overrides ignore_merges)
            by_user (bool): If True, include user information in the results
            focus_user (str): If provided, only analyze commits by this user (case insensitive, partial match)
            
        Returns:
            DataFrame: DataFrame with dates and line changes
            dict: User statistics (if by_user=True)
        """
        print(f"Analyzing repository: {workspace}/{repo_slug}")
        
        if file_extensions:
            print(f"Filtering by file extensions: {', '.join(file_extensions)}")
            
        commits = self.get_commits(workspace, repo_slug, start_date, end_date)
        if not commits:
            print("No commits found in the specified date range.")
            return None
        
        print(f"Found {len(commits)} commits")
        
        # Debug: Show sample author names if focus_user is specified
        if focus_user:
            print(f"Looking for user: '{focus_user}'")
            author_names = set()
            for i in range(min(10, len(commits))):
                commit = commits[i]
                if self.is_stash:
                    author_name = commit.get('author', {}).get('displayName', 'Unknown')
                else:
                    author_info = commit.get('author', {})
                    author_name = author_info.get('user', {}).get('display_name', 'Unknown')
                author_names.add(author_name)
            
            print(f"Sample author names in repository: {list(author_names)}")
            
            # Check if any match the focus_user
            matching_authors = []
            for author in author_names:
                if self.is_user_match(author, focus_user):
                    matching_authors.append(author)
            
            if matching_authors:
                print(f"Found matching authors: {matching_authors}")
            else:
                print(f"WARNING: No author names match '{focus_user}' in sample of {len(author_names)} authors")
        
        # Sample a few commits for debugging
        for i in range(min(3, len(commits))):
            commit = commits[i]
            if self.is_stash:
                commit_hash = commit['id']
                author_timestamp_ms = commit.get('authorTimestamp', 0)
                committer_timestamp_ms = commit.get('committerTimestamp', author_timestamp_ms)
                author_date = datetime.fromtimestamp(author_timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
                committer_date = datetime.fromtimestamp(committer_timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
                if author_timestamp_ms != committer_timestamp_ms:
                    print(f"Commit {commit_hash[:8]}: (author: {author_date}, committer: {committer_date})")
            else:
                commit_hash = commit['hash']
                author_date = parse(commit.get('date', '1970-01-01T00:00:00Z'))
                committer_date = parse(commit.get('committer_date', commit.get('date', '1970-01-01T00:00:00Z')))
                if author_date != committer_date:
                    print(f"Commit {commit_hash[:8]}: (author: {author_date}, committer: {committer_date})")
                    
        # Process commits in parallel with optimized settings
        data, user_data = self.analyze_commits_parallel(
            commits=commits,
            workspace=workspace,
            repo_slug=repo_slug,
            file_extensions=file_extensions,
            focus_user=focus_user,
            ignore_merges=ignore_merges,
            include_merges=include_merges,
            by_user=by_user,
            max_workers=5  # Reduced from 10 to prevent overwhelming the API
        )
        
        if focus_user:
            if data:
                print(f"Processed {len(data)} commits from user matching '{focus_user}'")
            else:
                print(f"No commits found from user matching '{focus_user}'")
            
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Group by date
        if not df.empty:
            if group_by == 'day':
                df['date'] = pd.to_datetime(df['date'])
            elif group_by == 'week':
                df['date'] = pd.to_datetime(df['date'])
                df['date'] = df['date'] - pd.to_timedelta(df['date'].dt.dayofweek, unit='D')
            elif group_by == 'month':
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-01')
                df['date'] = pd.to_datetime(df['date'])
            
            grouped = df.groupby('date').agg({
                'additions': 'sum',
                'deletions': 'sum'
            }).reset_index()
            
            # Sort by date
            grouped = grouped.sort_values('date')
        else:
            # Create an empty DataFrame with the right columns if no data
            grouped = pd.DataFrame(columns=['date', 'additions', 'deletions'])
        
        # Calculate user statistics if requested
        if by_user and user_data:
            # Process user data
            user_stats = []
            for name, stats in user_data.items():
                user_stats.append({
                    'name': name,
                    'email': stats['email'],
                    'commits': stats['commits'],
                    'additions': stats['additions'],
                    'deletions': stats['deletions'],
                    'total_changes': stats['additions'] + stats['deletions']
                })
                
            # Create DataFrame and sort by total changes
            if user_stats:
                user_df = pd.DataFrame(user_stats).sort_values('total_changes', ascending=False)
                print(f"Generated user statistics for {len(user_df)} users")
            else:
                user_df = pd.DataFrame(columns=['name', 'email', 'commits', 'additions', 'deletions', 'total_changes'])
                print("No user data was generated")
                
            return grouped, user_df
        
        return grouped
    
    def visualize_changes(self, data, workspace, repo_slug, group_by='day'):
        """
        Visualize code changes over time.
        
        Args:
            data (DataFrame): DataFrame with dates and line changes
            workspace (str): Bitbucket workspace
            repo_slug (str): Repository slug
            group_by (str): How the data is grouped ('day', 'week', 'month')
            
        Returns:
            None
        """
        if data is None or len(data) == 0:
            print("No data to visualize")
            return
            
        plt.figure(figsize=(12, 6))
        
        # Plot additions
        plt.bar(data['date'], data['additions'], color='green', alpha=0.6, label='Additions')
        
        # Plot deletions as negative values
        plt.bar(data['date'], -data['deletions'], color='red', alpha=0.6, label='Deletions')
        
        # Customize plot
        plt.title(f'Code Changes in {workspace}/{repo_slug}')
        plt.xlabel(f'Date (grouped by {group_by})')
        plt.ylabel('Lines of Code')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Format dates on x-axis
        plt.gcf().autofmt_xdate()
        
        # Add summary statistics as text
        total_additions = data['additions'].sum()
        total_deletions = data['deletions'].sum()
        total_changes = total_additions + total_deletions
        plt.figtext(
            0.5, 0.01, 
            f'Total changes: {total_changes} lines (Additions: {total_additions}, Deletions: {total_deletions})', 
            ha='center', 
            fontsize=12, 
            bbox={'facecolor': 'lightgray', 'alpha': 0.5, 'pad': 5}
        )
        
        # Save figure
        plt.savefig(f'{workspace}_{repo_slug}_loc_changes.png', dpi=300, bbox_inches='tight')
        print(f"Visualization saved as '{workspace}_{repo_slug}_loc_changes.png'")
        
        # Show plot
        plt.tight_layout()
        plt.show()
    
    def print_user_statistics(self, user_df, workspace, repo_slug):
        """
        Print user-level statistics.
        
        Args:
            user_df (DataFrame): DataFrame with user statistics
            workspace (str): Bitbucket workspace
            repo_slug (str): Repository slug
            
        Returns:
            None
        """
        if user_df is None or user_df.empty:
            print("No user data to display")
            return
            
        print("\nUser Statistics:")
        print("--------------")
        
        # Ensure required columns exist
        required_columns = ['name', 'email', 'additions', 'deletions', 'total_changes', 'commits']
        if not all(col in user_df.columns for col in required_columns):
            print("User DataFrame is missing required columns. Available columns:", list(user_df.columns))
            print("User data content (first row):", user_df.iloc[0].to_dict() if not user_df.empty else "No data")
            return
            
        # Print top contributors sorted by total changes
        print("\nTop Contributors by LOC:")
        for idx, row in user_df.head(10).iterrows():
            print(f"{idx+1}. {row['name']} - {int(row['additions'])} additions, {int(row['deletions'])} deletions, {int(row['total_changes'])} total changes")
        
        # Export user data to CSV
        user_summary_file = f"{workspace}_{repo_slug}_user_stats.csv"
        user_df.to_csv(user_summary_file, index=False)
        print(f"Exported user summary to {user_summary_file}")
        
        # Generate user visualization
        plt.figure(figsize=(12, 6))
        
        # Plot top users (up to 5)
        top_users = user_df.head(5)
        plt.bar(top_users['name'], top_users['total_changes'], color='blue', alpha=0.7)
        
        plt.title(f'Total Lines of Code Changed by Top Users in {workspace}/{repo_slug}')
        plt.xlabel('Users')
        plt.ylabel('Total Changes (Additions + Deletions)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save user chart
        user_chart_file = f"{workspace}_{repo_slug}_user_stats.png"
        plt.savefig(user_chart_file, dpi=300, bbox_inches='tight')
        print(f"User visualization saved as '{user_chart_file}'")
    
    def get_loc_changes_with_cloc(self, workspace, repo_slug, commit_hash, file_extensions=None):
        """
        Get lines of code changes using cloc by comparing current commit with its parent.
        
        Args:
            workspace (str): Bitbucket workspace or project key
            repo_slug (str): Repository slug
            commit_hash (str): Commit hash
            file_extensions (list): List of file extensions to include (e.g., ['.py', '.js'])
            
        Returns:
            dict: Dictionary with additions and deletions
        """
        # First check if it's a merge commit by getting commit info
        if self.is_stash:
            url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_hash}"
        else:
            url = f"{self.api_base}/repositories/{workspace}/{repo_slug}/commit/{commit_hash}"
            
        commit_info = self._make_request(url)
        
        # Skip merge commits (has more than one parent)
        if commit_info:
            parents = commit_info.get('parents', [])
            if self.is_stash and len(parents) > 1:
                return {'additions': 0, 'deletions': 0}
            elif not self.is_stash and len(parents) > 1:
                return {'additions': 0, 'deletions': 0}
        
        # Get parent commit hash
        parent_hash = None
        if self.is_stash and commit_info and commit_info.get('parents'):
            parent_hash = commit_info['parents'][0]['id']
        elif not self.is_stash and commit_info and commit_info.get('parents'):
            parent_hash = commit_info['parents'][0]['hash']
        
        if not parent_hash:
            print(f"Could not determine parent commit for {commit_hash}")
            return {'additions': 0, 'deletions': 0}
        
        # Create temporary directories for both commit versions
        with tempfile.TemporaryDirectory() as parent_dir, tempfile.TemporaryDirectory() as current_dir:
            try:
                # Download parent commit files
                if self.is_stash:
                    parent_archive_url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/archive?at={parent_hash}"
                    current_archive_url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/archive?at={commit_hash}"
                else:
                    parent_archive_url = f"{self.api_base}/repositories/{workspace}/{repo_slug}/src/{parent_hash}"
                    current_archive_url = f"{self.api_base}/repositories/{workspace}/{repo_slug}/src/{commit_hash}"
                
                # Download and extract archives for parent and current commit
                self._download_and_extract(parent_archive_url, parent_dir)
                self._download_and_extract(current_archive_url, current_dir)
                
                # Run cloc to get statistics
                result = self._run_cloc_comparison(parent_dir, current_dir, file_extensions)
                
                return {
                    'additions': result['added'],
                    'deletions': result['removed']
                }
                
            except Exception as e:
                print(f"Error using cloc for LOC calculation: {e}")
                # Fallback to the traditional method
                print("Falling back to traditional diff method")
                return self.get_loc_changes(workspace, repo_slug, commit_hash, file_extensions)
                
    def _download_and_extract(self, url, target_dir):
        """
        Download and extract repository archive from Bitbucket.
        
        Args:
            url (str): URL to download the archive
            target_dir (str): Directory to extract the archive to
        """
        # Use temp file to store the archive
        with tempfile.NamedTemporaryFile(suffix='.zip') as tmp_file:
            # Download archive
            response = requests.get(url, headers=self.headers, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp_file.write(chunk)
                    
            tmp_file.flush()
            
            # Extract archive
            shutil.unpack_archive(tmp_file.name, target_dir, format='zip')
            
    def _run_cloc_comparison(self, dir1, dir2, file_extensions=None):
        """
        Run cloc to compare two directories.
        
        Args:
            dir1 (str): Directory for the parent commit
            dir2 (str): Directory for the current commit
            file_extensions (list): List of file extensions to include
            
        Returns:
            dict: Dictionary with added, removed, and modified lines
        """
        try:
            # Check if cloc is installed
            subprocess.run(['cloc', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            
            # Build file extension filter
            ext_filter = []
            if file_extensions:
                ext_filter = ['--include-ext=' + ','.join(ext.lstrip('.') for ext in file_extensions)]
            
            # Run cloc on both directories
            cmd = ['cloc', '--diff', dir1, dir2, '--json'] + ext_filter
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            
            # Parse JSON output
            data = json.loads(result.stdout)
            
            # Extract summary
            same_files_modified = data.get('SUM', {}).get('same', {})
            
            # Handle different CLOC output formats
            if isinstance(same_files_modified, dict):
                modified_added = same_files_modified.get('added', 0)
                modified_removed = same_files_modified.get('removed', 0)
            else:
                modified_added = 0
                modified_removed = 0
                
            # Get the added/removed lines, ensuring they're integers
            added_lines = int(data.get('SUM', {}).get('added', 0))
            removed_lines = int(data.get('SUM', {}).get('removed', 0))
            
            # Ensure modified added/removed are integers
            if not isinstance(modified_added, int):
                modified_added = 0
            if not isinstance(modified_removed, int):
                modified_removed = 0
            
            return {
                'additions': added_lines + modified_added,
                'deletions': removed_lines + modified_removed
            }
            
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error running cloc: {e}")
            # If there's an error with cloc or parsing its output,
            # return zeros to let the caller know it didn't work
            return {'added': 0, 'removed': 0}
    
    def _make_request(self, url, params=None):
        """
        Helper method to make API requests with proper error handling and caching.
        
        Args:
            url (str): The API endpoint URL
            params (dict): Query parameters
            
        Returns:
            dict: The JSON response
        """
        # Try to get from cache first
        cached_data = self.cache.get(url, params)
        if cached_data:
            print(f"Using cached response for: {url}")
            return cached_data
            
        try:
            # Some corporate environments might require SSL verification to be disabled
            # or specific certificates. For production use, it's better to configure
            # proper certificates rather than disabling verification.
            verify = True
            
            print(f"Making request to: {url}")
            print(f"Headers: {self.headers}")
            print(f"Parameters: {params}")
            
            # Always use Bearer token authentication
            print("Using Bearer token authentication")
            response = requests.get(url, headers=self.headers, params=params, verify=verify, timeout=30)
            
            print(f"Response status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            # Print the first 500 characters of the response for debugging
            response_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
            print(f"Response preview: {response_preview}")
                
            # Check for HTTP errors
            response.raise_for_status()
            
            # Only try to parse as JSON if we got content and it's JSON content
            if response.text.strip():
                content_type = response.headers.get('Content-Type', '')
                if 'json' in content_type or response.text.strip().startswith('{'):
                    response_data = response.json()
                    # Cache the successful response
                    self.cache.set(url, params, response_data)
                    return response_data
                else:
                    print(f"Warning: Response is not JSON. Content-Type: {content_type}")
                    print("Returning empty dict")
                    return {}
            else:
                print("Empty response received")
                return {}
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            if response.status_code == 401:
                print("Authentication error. Please check your credentials or token.")
            elif response.status_code == 403:
                print("Permission denied. Please check if your token has sufficient permissions.")
            elif response.status_code == 404:
                print(f"Resource not found. Please check if the URL is correct: {url}")
                print("This could indicate an incorrect API path or that the repository doesn't exist.")
            
            try:
                error_details = response.json()
                print(f"Error details: {error_details}")
            except:
                print(f"Error response: {response.text}")
            return None
        except requests.exceptions.SSLError as e:
            print(f"SSL Certificate error: {e}")
            print("If you're in a corporate environment, you may need to use a custom certificate.")
            print("Try modifying the code to disable SSL verification (verify=False) for testing purposes only.")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {e}")
            print(f"Please check if the URL {url} is correct and accessible.")
            print("This could indicate network issues or an incorrect base URL.")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print("The server response isn't valid JSON. Response content:")
            print(response.text[:1000])  # Print first 1000 chars of response
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
    
    def _should_skip_file(self, filepath):
        """
        Identify files to exclude from LOC calculations.
        
        Args:
            filepath (str): Path to the file
            
        Returns:
            bool: True if file should be skipped
        """
        # Skip binary files, generated code, etc.
        skip_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.bmp', '.tiff',  
                           '.zip', '.tar', '.gz', '.rar', '.7z', '.jar', '.war', '.ear', 
                           '.class', '.pyc', '.pyo', '.o', '.obj', '.dll', '.exe', '.so', '.dylib',
                           '.min.js', '.min.css', '.pdf', '.doc', '.docx', '.ppt', '.pptx',
                           '.xls', '.xlsx', '.svg', '.ttf', '.woff', '.woff2', '.eot',
                           '.mp3', '.mp4', '.avi', '.mov', '.flv', '.webm', '.lock']
                           
        skip_paths = ['node_modules/', 'dist/', 'build/', 'target/', '__pycache__/', 
                      '.git/', '.svn/', '.idea/', '.vscode/', '.gradle/', 
                      'vendor/', 'bin/', 'obj/']
        
        # Check extensions
        if any(filepath.lower().endswith(ext) for ext in skip_extensions):
            return True
            
        # Check paths
        if any(path in filepath for path in skip_paths):
            return True
            
        return False
        
    def get_loc_changes(self, workspace, repo_slug, commit_hash, file_extensions=None):
        """
        Get commit statistics (additions and deletions) with optimized calculation.
        
        Args:
            workspace (str): Bitbucket workspace or project key
            repo_slug (str): Repository slug
            commit_hash (str): Commit hash
            file_extensions (list): List of file extensions to include (e.g., ['.py', '.js'])
            
        Returns:
            dict: Dictionary with additions and deletions
        """
        if self.is_stash:
            # First check if it's a merge commit by getting commit info
            url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_hash}"
            commit_info = self._make_request(url)
            
            # Skip merge commits (has more than one parent)
            if commit_info and len(commit_info.get('parents', [])) > 1:
                return {'additions': 0, 'deletions': 0}
            
            # For Stash/Bitbucket Server - get detailed diff information for more accurate counts
            url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_hash}/diff"
        else:
            # For Bitbucket Cloud
            url = f"{self.api_base}/repositories/{workspace}/{repo_slug}/diffstat/{commit_hash}"
        
        # Make the request using our helper method
        response_json = self._make_request(url)
        
        if not response_json:
            # If request failed, return zeros
            return {'additions': 0, 'deletions': 0}
        
        # Calculate additions and deletions from diff statistics
        additions = 0
        deletions = 0
        
        if self.is_stash:
            # Stash/Bitbucket Server format - improved processing
            for diff_file in response_json.get('diffs', []):
                # Check file extension if specified
                source = diff_file.get('source')
                destination = diff_file.get('destination')
                file_path = ''
                
                if source is not None:
                    file_path = source.get('toString', '')
                elif destination is not None:
                    file_path = destination.get('toString', '')
                
                # Skip binary files and check extensions
                if self._should_skip_file(file_path):
                    continue
                    
                if file_extensions and not any(file_path.endswith(ext) for ext in file_extensions):
                    continue
                
                # Process each file's hunks - optimized to count lines in one pass
                for hunk in diff_file.get('hunks', []):
                    for segment in hunk.get('segments', []):
                        segment_type = segment.get('type')
                        lines_count = len(segment.get('lines', []))
                        
                        if segment_type == 'ADDED':
                            additions += lines_count
                        elif segment_type == 'REMOVED':
                            deletions += lines_count
        else:
            # Bitbucket Cloud format - optimized processing
            for file in response_json.get('values', []):
                # Get file path
                file_path = file.get('new', {}).get('path', '') or file.get('old', {}).get('path', '')
                
                # Skip binary files and check extensions
                if self._should_skip_file(file_path):
                    continue
                    
                if file_extensions and not any(file_path.endswith(ext) for ext in file_extensions):
                    continue
                    
                # Add up additions and deletions from each file
                additions += file.get('lines_added', 0)
                deletions += file.get('lines_removed', 0)
        
        return {
            'additions': additions,
            'deletions': deletions
        }
    
    def normalize_username(self, username):
        """
        Normalize usernames for better matching across different formats.
        
        Args:
            username (str): Username or email to normalize
            
        Returns:
            str: Normalized username or None if input is None
        """
        if not username:
            return None
            
        # Convert to lowercase and remove whitespace
        normalized = username.strip().lower()
        
        # Extract username from email if present
        if '@' in normalized:
            normalized = normalized.split('@')[0]
            
        # Convert dots and underscores to spaces for better matching
        normalized = normalized.replace('.', ' ').replace('_', ' ')
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Handle common naming variations
        name_mappings = {
            'robert': 'rob',
            'michael': 'mike',
            'matthew': 'matt',
            'christopher': 'chris',
            'richard': 'rick',
            'jonathan': 'jon',
            'nicholas': 'nick',
            'daniel': 'dan',
            'william': 'will',
            'benjamin': 'ben',
            'alexander': 'alex',
            'katherine': 'kate',
            'jennifer': 'jen',
            'elizabeth': 'liz',
            'stephanie': 'steph',
            'deborah': 'deb'
        }
        
        for full, short in name_mappings.items():
            if normalized == full:
                return short
                
        return normalized

    def is_user_match(self, username1, username2):
        """
        Check if two usernames match with very strict filtering for focus_user.
        This function handles various name formats, email addresses, and reversed names.
        
        Args:
            username1 (str): First username (from commit author name or email)
            username2 (str): Second username (focus_user from UI input, could be email or name)
            
        Returns:
            bool: True if usernames match with strict criteria
        """
        if not username1 or not username2:
            return False
            
        # Clean both inputs
        user1_clean = username1.lower().strip()
        user2_clean = username2.lower().strip()
        
        # Exact match (case-insensitive)
        if user1_clean == user2_clean:
            return True
        
        # Email-based matching - check if either user1 or user2 is an email
        if '@' in user2_clean:
            # user2 is an email address
            if '@' in user1_clean:
                # Both are emails - exact match
                return user1_clean == user2_clean
            else:
                # user1 is name, user2 is email - check if email parts match name parts
                email_prefix = user2_clean.split('@')[0]
                
                # Check if the email prefix parts are in the name
                if '.' in email_prefix:
                    email_parts = email_prefix.split('.')
                    
                    # Check if name contains email parts
                    name_words = user1_clean.replace(',', ' ').replace('(', ' ').replace(')', ' ').split()
                    
                    # Look for matches between email parts and name words
                    matches = 0
                    for email_part in email_parts:
                        if len(email_part) >= 3:  # Only consider meaningful parts
                            for name_word in name_words:
                                if email_part in name_word or name_word in email_part:
                                    matches += 1
                                    break
                    
                    # If we found matches for most email parts, consider it a match
                    if matches >= len(email_parts) * 0.6:  # At least 60% of parts should match
                        return True
                
                # Also check if email prefix matches any part of the name directly
                name_normalized = user1_clean.replace(',', '').replace('(', '').replace(')', '').replace(' ', '')
                email_normalized = email_prefix.replace('.', '')
                if email_normalized in name_normalized or name_normalized in email_normalized:
                    return True
                    
                return False
        elif '@' in user1_clean:
            # user1 is email, user2 is not email - use same logic in reverse
            return self.is_user_match(username2, username1)
            if '.' in email_prefix:
                email_parts = email_prefix.split('.')
                name_parts = user2_clean.replace(',', ' ').split()
                # Check if any significant name part matches email parts
                for name_part in name_parts:
                    if len(name_part) >= 3 and name_part in email_parts:
                        return True
            
        # Name-based matching (fallback when no email involved)
        # Normalize both usernames for comparison
        norm1 = self.normalize_username(username1)
        norm2 = self.normalize_username(username2)
        
        # Exact normalized match
        if norm1 and norm2 and norm1 == norm2:
            return True
        
        # Handle reversed name formats (e.g., "Kallatti, Manjunath" vs "Manjunath Kallatti")
        def split_name_parts(name):
            """Split name into parts, handling commas and spaces"""
            # Remove common punctuation and split
            clean_name = name.replace(',', ' ').replace('.', ' ').replace('_', ' ')
            parts = [part.strip().lower() for part in clean_name.split() if part.strip()]
            return set(parts)  # Use set for order-independent comparison
            
        user1_parts = split_name_parts(username1)
        user2_parts = split_name_parts(username2)
        
        # Check if all parts of the shorter name are in the longer name
        if len(user2_parts) >= 2 and len(user1_parts) >= 2:
            # For multi-part names, check if they contain the same significant parts
            if user2_parts.issubset(user1_parts) or user1_parts.issubset(user2_parts):
                return True
        
        # Check if the focus_user is a meaningful substring (at least 3 chars)
        if len(user2_clean) >= 3:
            # Only match if focus_user appears as a complete word or substantial substring
            if user2_clean in user1_clean:
                # Additional check: make sure it's not a tiny substring that causes false matches
                if len(user2_clean) >= 4 or user2_clean == user1_clean:
                    return True
        
        # Special handling for name parts
        # If focus_user has multiple words, check if any significant part matches
        focus_parts = [part for part in user2_clean.replace(',', ' ').split() if len(part) >= 3]
        for part in focus_parts:
            if part in user1_clean:
                return True
                
        return False
    
    def _process_single_commit(self, commit, workspace, repo_slug, file_extensions=None, 
                           focus_user=None, ignore_merges=False, include_merges=False, by_user=False):
        """
        Process a single commit and return its data.
        
        Args:
            commit (dict): Commit data
            workspace (str): Bitbucket workspace
            repo_slug (str): Repository slug
            file_extensions (list): List of file extensions to include
            focus_user (str): If provided, only process if commit is by this user
            ignore_merges (bool): If True, ignore merge commits
            include_merges (bool): If True, include merge commits
            by_user (bool): If True, include user information
            
        Returns:
            dict: Processed commit data or None if commit should be skipped
        """
        if self.is_stash:
            # Stash/Bitbucket Server format
            commit_hash = commit['id']
            
            # Get both author and committer timestamps (Unix epoch milliseconds)
            author_timestamp_ms = commit.get('authorTimestamp', 0)
            committer_timestamp_ms = commit.get('committerTimestamp', author_timestamp_ms)
            
            # Use the later of the two timestamps
            timestamp_ms = max(author_timestamp_ms, committer_timestamp_ms)
            commit_date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
            
            # Get author information for user-level stats
            author_name = commit.get('author', {}).get('displayName', 'Unknown')
            author_email = commit.get('author', {}).get('emailAddress', '')
            
            # Filter by user if focus_user is provided
            if focus_user and not self.is_user_match(author_name, focus_user):
                return None
            
            # Handle merge commits based on flags
            is_merge = commit.get('message', '').startswith('Merge ')
            if is_merge and ignore_merges and not include_merges:
                return None
        else:
            # Bitbucket Cloud format
            commit_hash = commit['hash']
            
            # Parse both timestamps (if available)
            author_date = parse(commit.get('date', '1970-01-01T00:00:00Z'))
            committer_date = parse(commit.get('committer_date', commit.get('date', '1970-01-01T00:00:00Z')))
            
            # Use the later of the two timestamps
            commit_date = max(author_date, committer_date).strftime('%Y-%m-%d')
            
            # Get author information for user-level stats
            author_info = commit.get('author', {})
            author_name = author_info.get('user', {}).get('display_name', 'Unknown')
            author_email = author_info.get('raw', '').split('<')[-1].strip('>')
            
            # Filter by user if focus_user is provided
            if focus_user and not self.is_user_match(author_name, focus_user):
                return None
                
            # Handle merge commits based on flags
            is_merge = commit.get('message', '').startswith('Merge ')
            if is_merge and ignore_merges and not include_merges:
                return None
            
        # Try to use cloc for LOC calculation, fall back to traditional method if it fails
        try:
            stats = self.get_loc_changes_with_cloc(workspace, repo_slug, commit_hash, file_extensions)
        except Exception:
            stats = self.get_loc_changes(workspace, repo_slug, commit_hash, file_extensions)
        
        # Prepare entry for time-series data
        entry = {
            'date': commit_date,
            'additions': stats['additions'],
            'deletions': stats['deletions']
        }
        
        # Add author info if requested
        if by_user:
            entry['author'] = author_name
            entry['email'] = author_email
            
        return entry
    
    def analyze_commits_parallel(self, commits, workspace, repo_slug, file_extensions=None,
                              focus_user=None, ignore_merges=False, include_merges=False, 
                              by_user=False, max_workers=10):
        """
        Process commits in parallel for faster analysis.
        
        Args:
            commits (list): List of commits to process
            workspace (str): Bitbucket workspace
            repo_slug (str): Repository slug
            file_extensions (list): List of file extensions to include
            focus_user (str): If provided, only process if commit is by this user
            ignore_merges (bool): If True, ignore merge commits
            include_merges (bool): If True, include merge commits
            by_user (bool): If True, include user information
            max_workers (int): Maximum number of worker threads
            
        Returns:
            list: List of processed commit data
            dict: User statistics if by_user is True
        """
        results = []
        user_data = {}
        filtered_commit_count = 0
        total_commits = len(commits)
        
        print(f"Processing {total_commits} commits in parallel with {max_workers} workers")
        
        # Use smaller batch size if there are fewer commits
        workers = min(max_workers, max(1, total_commits // 5))
        
        # Create a progress bar
        with tqdm(total=total_commits, desc="Processing commits") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                # Submit all commits for processing
                future_to_commit = {
                    executor.submit(
                        self._process_single_commit, 
                        commit, 
                        workspace, 
                        repo_slug, 
                        file_extensions,
                        focus_user,
                        ignore_merges,
                        include_merges,
                        by_user
                    ): i for i, commit in enumerate(commits)
                }
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_commit):
                    commit_index = future_to_commit[future]
                    pbar.update(1)
                    
                    try:
                        entry = future.result()
                        if entry:
                            results.append(entry)
                            
                            # Update user statistics if requested
                            if by_user:
                                author_name = entry['author']
                                if author_name not in user_data:
                                    user_data[author_name] = {
                                        'name': author_name,
                                        'email': entry['email'],
                                        'commits': 0,
                                        'additions': 0,
                                        'deletions': 0
                                    }
                                
                                user_data[author_name]['commits'] += 1
                                user_data[author_name]['additions'] += entry['additions']
                                user_data[author_name]['deletions'] += entry['deletions']
                        else:
                            filtered_commit_count += 1
                    except Exception as exc:
                        commit_id = commits[commit_index].get('id', commits[commit_index].get('hash', 'unknown'))
                        print(f"Error processing commit {commit_id}: {exc}")
        
        print(f"Successfully processed {len(results)} commits, filtered {filtered_commit_count}")
        
        return results, user_data
    
def check_cloc_installation():
    """
    Check if cloc is installed on the system.
    
    Returns:
        bool: True if cloc is installed, False otherwise
    """
    try:
        result = subprocess.run(['cloc', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print(f"Found cloc version: {result.stdout.decode('utf-8').strip()}")
            return True
    except FileNotFoundError:
        print("cloc command not found.")
        print("Please install cloc to use advanced LOC statistics:")
        print("  - macOS: brew install cloc")
        print("  - Linux: apt-get install cloc  or  yum install cloc")
        print("  - Windows: choco install cloc  or download from https://github.com/AlDanial/cloc")
        return False
    return False


def main():
    """Main entry point of the script."""
    parser = argparse.ArgumentParser(description='Analyze Bitbucket repository for lines of code changes')
    parser.add_argument('workspace', help='Bitbucket workspace/project (team or user)')
    parser.add_argument('repo_slug', help='Repository slug (name)')
    parser.add_argument('--token', help='Bitbucket access token for Bearer authentication')
    parser.add_argument('--base-url', help='Base URL for self-hosted Bitbucket/Stash instance')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--group-by', choices=['day', 'week', 'month'], default='day',
                        help='How to group the results (default: day)')
    parser.add_argument('--test-connection', action='store_true',
                        help='Test connection to Bitbucket server without retrieving commits')
    parser.add_argument('--export', help='Export data to CSV file')
    parser.add_argument('--file-extensions', nargs='+', 
                        help='Filter by file extensions (e.g., .py .js .tsx)')
    parser.add_argument('--ignore-merges', action='store_true',
                        help='Ignore merge commits')
    parser.add_argument('--include-merges', action='store_true',
                        help='Include merge commits (takes precedence over --ignore-merges)')
    parser.add_argument('--by-user', action='store_true',
                        help='Generate per-user statistics')
    parser.add_argument('--use-cloc', action='store_true', default=True,
                        help='Use cloc for calculating lines of code (default: True)')
    
    args = parser.parse_args()
    
    # Use environment variables if token not provided in command line
    token = args.token if args.token else os.environ.get('BITBUCKET_TOKEN')
    base_url = args.base_url if args.base_url else os.environ.get('BITBUCKET_BASE_URL')
    
    # Require token for authentication
    if not token:
        print("Error: Bearer token is required for authentication.")
        print("Please provide a token using the --token parameter or set the BITBUCKET_TOKEN environment variable.")
        return
    
    # Check if cloc is installed if use_cloc is True
    if args.use_cloc:
        has_cloc = check_cloc_installation()
        if not has_cloc:
            print("Warning: cloc is not installed. Falling back to traditional diff method.")
    
    analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
    
    # Test connection if requested
    if args.test_connection:
        if analyzer.test_connection(args.workspace, args.repo_slug):
            print("\nConnection test successful! ✅")
            print("Server is reachable and authentication is working.")
            return 0
        else:
            print("\nConnection test failed! ❌")
            print("Please check the error messages above for more details.")
            return 1
    
    # Run the full analysis
    print(f"Starting analysis of {args.workspace}/{args.repo_slug}...")
    result = analyzer.analyze_repository(
        args.workspace, 
        args.repo_slug, 
        start_date=args.start_date, 
        end_date=args.end_date,
        group_by=args.group_by,
        file_extensions=args.file_extensions,
        ignore_merges=args.ignore_merges,
        include_merges=args.include_merges,
        by_user=args.by_user
    )
    
    # Handle both standard and user-level analysis results
    # Unpack result - if by_user is True, result will be a tuple (data, user_df)
    if result is None:
        print("No data returned from analysis.")
        return
        
    if args.by_user and isinstance(result, tuple) and len(result) == 2:
        data, user_df = result
        print(f"Successfully unpacked data and user statistics.")
        print(f"User data contains {len(user_df)} entries.")
    else:
        data = result
        user_df = None
        print(f"Analysis returned only repository data, no user statistics.")
    
    if data is not None:
        print("\nCode changes summary:")
        total_additions = data['additions'].sum()
        total_deletions = data['deletions'].sum()
        total_changes = total_additions + total_deletions
        print(f"Total additions: {total_additions} lines")
        print(f"Total deletions: {total_deletions} lines")
        print(f"Total changes: {total_changes} lines (sum of additions and deletions)")
        
        # Export data if requested
        if args.export:
            export_path = args.export
            if not export_path.endswith('.csv'):
                export_path += '.csv'
            data.to_csv(export_path, index=False)
            print(f"Data exported to {export_path}")
        
        analyzer.visualize_changes(data, args.workspace, args.repo_slug, args.group_by)
        
        # Output user statistics if requested
        if args.by_user and user_df is not None:
            print("\nCalculating user statistics...")
            if not user_df.empty:
                analyzer.print_user_statistics(user_df, args.workspace, args.repo_slug)
            else:
                print("No user statistics data available to display.")


if __name__ == '__main__':
    import sys
    sys.exit(main() or 0)
