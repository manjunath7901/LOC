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
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta


class BitbucketLOCAnalyzer:
    def __init__(self, base_url=None, token=None):
        """Initialize the analyzer with Bitbucket/Stash credentials.
        
        Args:
            base_url (str): Base URL for self-hosted Bitbucket/Stash instance (e.g. https://stash.example.com)
            token (str): Bitbucket access token for Bearer authentication
        """
        self.headers = {}
        self.auth = None
        
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
                          file_extensions=None, ignore_merges=False, include_merges=False, by_user=False):
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
        
        data = []
        user_data = {}  # For tracking per-user statistics
        
        for i, commit in enumerate(commits):
            if self.is_stash:
                # Stash/Bitbucket Server format
                commit_hash = commit['id']
                
                # Get both author and committer timestamps (Unix epoch milliseconds)
                author_timestamp_ms = commit.get('authorTimestamp', 0)
                committer_timestamp_ms = commit.get('committerTimestamp', author_timestamp_ms)
                
                # Use the later of the two timestamps (improvement from issue #XXX)
                # This ensures that commits merged recently will be included in time-based queries
                # even if they were authored much earlier
                timestamp_ms = max(author_timestamp_ms, committer_timestamp_ms)
                commit_date = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
                
                # Get author information for user-level stats
                author_name = commit.get('author', {}).get('displayName', 'Unknown')
                author_email = commit.get('author', {}).get('emailAddress', '')
                
                if i < 3:  # Debug for first few commits
                    author_date = datetime.fromtimestamp(author_timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    committer_date = datetime.fromtimestamp(committer_timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    if author_timestamp_ms != committer_timestamp_ms:
                        print(f"Commit {commit_hash[:8]}: Using {commit_date} (author: {author_date}, committer: {committer_date})")
                
                # Handle merge commits based on flags
                is_merge = commit.get('message', '').startswith('Merge ')
                if is_merge and ignore_merges and not include_merges:
                    continue
            else:
                # Bitbucket Cloud format
                commit_hash = commit['hash']
                
                # For Bitbucket Cloud, we have different timestamp formats
                # Parse both timestamps (if available)
                author_date = parse(commit.get('date', '1970-01-01T00:00:00Z'))
                committer_date = parse(commit.get('committer_date', commit.get('date', '1970-01-01T00:00:00Z')))
                
                # Use the later of the two timestamps
                # This ensures that commits merged recently will be included in time-based queries
                commit_date = max(author_date, committer_date).strftime('%Y-%m-%d')
                
                # Get author information for user-level stats
                author_info = commit.get('author', {})
                author_name = author_info.get('user', {}).get('display_name', 'Unknown')
                author_email = author_info.get('raw', '').split('<')[-1].strip('>')
                
                if i < 3:  # Debug for first few commits
                    if author_date != committer_date:
                        print(f"Commit {commit_hash[:8]}: Using {commit_date} (author: {author_date}, committer: {committer_date})")
                
                # Handle merge commits based on flags
                is_merge = commit.get('message', '').startswith('Merge ')
                if is_merge and ignore_merges and not include_merges:
                    continue
                
            # Try to use cloc for LOC calculation, fall back to traditional method if it fails
            try:
                stats = self.get_loc_changes_with_cloc(workspace, repo_slug, commit_hash, file_extensions)
                print(f"Using cloc to calculate LOC changes for {commit_hash[:8]}")
            except Exception as e:
                print(f"Failed to use cloc for LOC calculation: {e}")
                print(f"Falling back to traditional diff method for {commit_hash[:8]}")
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
            
            data.append(entry)
            
            # Track user stats
            if by_user:
                if author_name not in user_data:
                    user_data[author_name] = {
                        'name': author_name,
                        'email': author_email,
                        'commits': 0,
                        'additions': 0,
                        'deletions': 0
                    }
                
                user_data[author_name]['commits'] += 1
                user_data[author_name]['additions'] += stats['additions']
                user_data[author_name]['deletions'] += stats['deletions']
            
            # Print progress every 10 commits
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(commits)} commits")
        
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
        if data is None or data.empty:
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
            print("User data content (first row):", user_df.iloc[0].to_dict() if len(user_df) > 0 else "No data")
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
        Helper method to make API requests with proper error handling.
        
        Args:
            url (str): The API endpoint URL
            params (dict): Query parameters
            
        Returns:
            dict: The JSON response
        """
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
                    return response.json()
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
    
    def get_loc_changes(self, workspace, repo_slug, commit_hash, file_extensions=None):
        """
        Get commit statistics (additions and deletions).
        
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
            if len(user_df) > 0:
                analyzer.print_user_statistics(user_df, args.workspace, args.repo_slug)
            else:
                print("No user statistics data available to display.")


if __name__ == '__main__':
    import sys
    sys.exit(main() or 0)
