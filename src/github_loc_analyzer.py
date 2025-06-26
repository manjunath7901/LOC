#!/usr/bin/env python3
"""
Bitbucket Lines of Code Analyzer

This script analyzes a Bitbucket repository to track lines added and deleted over time.
It uses the Bitbucket API to retrieve commit data and visualizes the changes.
"""

import argparse
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta


class BitbucketLOCAnalyzer:
    def __init__(self, username=None, password=None, token=None):
        """Initialize the analyzer with Bitbucket credentials.
        
        Args:
            username (str): Bitbucket username
            password (str): Bitbucket app password or password
            token (str): Bitbucket access token (alternative to username/password)
        """
        self.headers = {}
        self.auth = None
        
        if token:
            self.headers = {'Authorization': f'Bearer {token}'}
        elif username and password:
            self.auth = (username, password)
        
    def get_commits(self, workspace, repo_slug, start_date=None, end_date=None):
        """
        Get commits for a repository within a specified date range.
        
        Args:
            workspace (str): Bitbucket workspace (formerly known as team or username)
            repo_slug (str): Repository slug (repository name)
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            list: List of commit data
        """
        all_commits = []
        page = 1
        pagelen = 100  # Bitbucket uses 'pagelen' instead of 'per_page'
        
        # If no end date is provided, use current date
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # If no start date is provided, use date 3 months ago
        if not start_date:
            start_date = (datetime.now() - relativedelta(months=3)).strftime('%Y-%m-%d')
            
        print(f"Analyzing commits from {start_date} to {end_date}")
            
        while True:
            # Bitbucket API 2.0 endpoint
            url = f'https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/commits'
            params = {
                'pagelen': pagelen,
                'page': page
            }
            
            # Add date filters
            if start_date:
                # Convert to ISO 8601 format that Bitbucket accepts
                start_timestamp = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%SZ')
                params['since'] = start_timestamp
                
            if end_date:
                # Convert to ISO 8601 format
                end_timestamp = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%SZ')
                params['until'] = end_timestamp
            
            # Make the request
            if self.auth:
                response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
            else:
                response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                try:
                    print(response.json())
                except:
                    print(response.text)
                return []
            
            # Parse the response
            response_json = response.json()
            if 'values' not in response_json or not response_json['values']:
                break
                
            # Bitbucket returns a values array and next page URL
            commits = response_json['values']
            all_commits.extend(commits)
            
            # Check for next page URL
            if 'next' not in response_json:
                break
                
            # Get the next page URL
            url = response_json['next']
            # When using a direct URL, we don't need params anymore
            params = {}
            
        return all_commits
    
    def get_commit_stats(self, workspace, repo_slug, commit_hash):
        """
        Get statistics for a specific commit.
        
        Args:
            workspace (str): Bitbucket workspace
            repo_slug (str): Repository slug
            commit_hash (str): Commit hash
            
        Returns:
            dict: Dictionary with additions and deletions
        """
        # Bitbucket API doesn't provide direct commit stats like GitHub does
        # We need to get the diff and calculate additions/deletions from it
        url = f'https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/diffstat/{commit_hash}'
        
        if self.auth:
            response = requests.get(url, auth=self.auth, headers=self.headers)
        else:
            response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error retrieving commit stats: {response.status_code}")
            return {'additions': 0, 'deletions': 0}
        
        diff_data = response.json()
        
        # Calculate additions and deletions from diff statistics
        additions = 0
        deletions = 0
        for file in diff_data.get('values', []):
            # Add up additions and deletions from each file
            additions += file.get('lines_added', 0)
            deletions += file.get('lines_removed', 0)
        
        return {
            'additions': additions,
            'deletions': deletions
        }
    
    def analyze_repository(self, workspace, repo_slug, start_date=None, end_date=None, group_by='day'):
        """
        Analyze repository for lines added and deleted over time.
        
        Args:
            workspace (str): Bitbucket workspace
            repo_slug (str): Repository slug
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            group_by (str): How to group the results ('day', 'week', 'month')
            
        Returns:
            DataFrame: DataFrame with dates and line changes
        """
        print(f"Analyzing repository: {workspace}/{repo_slug}")
        
        commits = self.get_commits(workspace, repo_slug, start_date, end_date)
        if not commits:
            print("No commits found in the specified date range.")
            return None
        
        print(f"Found {len(commits)} commits")
        
        data = []
        for i, commit in enumerate(commits):
            commit_hash = commit['hash']
            commit_date = parse(commit['date']).strftime('%Y-%m-%d')
            stats = self.get_commit_stats(workspace, repo_slug, commit_hash)
            
            data.append({
                'date': commit_date,
                'additions': stats['additions'],
                'deletions': stats['deletions']
            })
            
            # Print progress every 10 commits
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(commits)} commits")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Group by date
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
        
        # Add net line count as text
        net_changes = data['additions'].sum() - data['deletions'].sum()
        sign = '+' if net_changes >= 0 else ''
        plt.figtext(
            0.5, 0.01, 
            f'Net change: {sign}{net_changes} lines', 
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


def main():
    """Main entry point of the script."""
    parser = argparse.ArgumentParser(description='Analyze Bitbucket repository for lines of code changes')
    parser.add_argument('workspace', help='Bitbucket workspace (team or user)')
    parser.add_argument('repo_slug', help='Repository slug (name)')
    parser.add_argument('--username', help='Bitbucket username')
    parser.add_argument('--password', help='Bitbucket app password or password')
    parser.add_argument('--token', help='Bitbucket access token')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--group-by', choices=['day', 'week', 'month'], default='day',
                        help='How to group the results (default: day)')
    
    args = parser.parse_args()
    
    # Use environment variables if credentials not provided in command line
    username = args.username if args.username else os.environ.get('BITBUCKET_USERNAME')
    password = args.password if args.password else os.environ.get('BITBUCKET_PASSWORD')
    token = args.token if args.token else os.environ.get('BITBUCKET_TOKEN')
    
    analyzer = BitbucketLOCAnalyzer(username=username, password=password, token=token)
    data = analyzer.analyze_repository(
        args.workspace, 
        args.repo_slug, 
        start_date=args.start_date, 
        end_date=args.end_date,
        group_by=args.group_by
    )
    
    if data is not None:
        print("\nCode changes summary:")
        print(f"Total additions: {data['additions'].sum()} lines")
        print(f"Total deletions: {data['deletions'].sum()} lines")
        print(f"Net change: {data['additions'].sum() - data['deletions'].sum()} lines")
        
        analyzer.visualize_changes(data, args.workspace, args.repo_slug, args.group_by)


if __name__ == '__main__':
    main()
