#!/usr/bin/env python3
"""
Bitbucket LOC Analyzer - Combined Direct & PR Contribution Tracker

This script analyzes a Bitbucket repository to track contributions by
both direct commits and pull requests, ensuring accurate attribution.
It combines the best of both approaches to provide a complete view
of each contributor's activity.
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import json
import argparse
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
import csv
import re
import sys

class BitbucketContributionTracker:
    def __init__(self, base_url, token):
        """Initialize the tracker with Bitbucket credentials.
        
        Args:
            base_url (str): Base URL for self-hosted Bitbucket/Stash instance
            token (str): Bitbucket access token for Bearer authentication
        """
        self.headers = {}
        self.base_url = base_url if base_url else "https://api.bitbucket.org"
        
        # Remove trailing slash if present
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
        
        # Check if this is a Stash/Bitbucket Server instance
        self.is_stash = "api.bitbucket.org" not in self.base_url
        
        # Prepare API base URL
        if self.is_stash:
            self.api_base = self.base_url
        else:
            self.api_base = f"{self.base_url}/2.0"
        
        # Set authentication headers
        if token:
            if token.startswith('Bearer '):
                self.headers['Authorization'] = token
            else:
                self.headers['Authorization'] = f'Bearer {token}'
            print(f"Using Bearer token authentication: {token[:5]}...")
        else:
            raise ValueError("A token must be provided for authentication")
    
    def get_all_commits(self, workspace, repo_slug, start_date=None, end_date=None):
        """
        Get all commits for a repository within a specified date range.
        
        Args:
            workspace (str): Bitbucket workspace/project key
            repo_slug (str): Repository slug (repository name)
            start_date (datetime): Start date
            end_date (datetime): End date
            
        Returns:
            list: List of commit data
        """
        all_commits = []
        start = 0
        limit = 100
        
        # For Stash/Bitbucket Server API
        url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
        
        print(f"Fetching all commits from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        while True:
            params = {
                'limit': limit,
                'start': start
            }
            
            # Make the request
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching commits: {e}")
                return all_commits
            
            # Process the commits
            for commit in data.get('values', []):
                # Parse the commit date
                commit_date_str = commit.get('authorTimestamp', 0)
                commit_date = datetime.fromtimestamp(commit_date_str / 1000)  # Convert from ms to seconds
                
                # Check if the commit is within our date range
                if (not start_date or commit_date >= start_date) and (not end_date or commit_date <= end_date):
                    all_commits.append(commit)
            
            # Check pagination
            is_last_page = data.get('isLastPage', True)
            if is_last_page:
                break
                
            # Update the start parameter for the next page
            start = data.get('nextPageStart')
        
        print(f"Found {len(all_commits)} commits in the date range")
        for commit in all_commits:
            print(f"Commit: {commit.get('id')[:8]}, Author: {commit.get('author', {}).get('displayName', 'Unknown')}, Date: {datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000)}")
        return all_commits
    
    def extract_pr_info(self, message):
        """
        Extract pull request number and title from a commit message.
        
        Args:
            message (str): The commit message
            
        Returns:
            dict: PR number and title or None if not a PR
        """
        # Common PR message patterns
        patterns = [
            r'Merge pull request #(\d+)[^\n]*\n\s*(.+)',  # GitHub/GitLab style
            r'Merged in .+ \(pull request #(\d+)\)[\s\S]*?Title: (.+)',  # Bitbucket style
            r'PR #(\d+)[^\n]*\n\s*(.+)',  # Simple PR reference
            r'pull request #(\d+)[^:]*: (.+)'  # Another common format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return {
                    'number': match.group(1),
                    'title': match.group(2).strip()
                }
        
        return None
    
    def get_commit_stats(self, workspace, repo_slug, commit_hash):
        """
        Get the lines added/deleted for a specific commit.
        
        Args:
            workspace (str): Bitbucket workspace/project key
            repo_slug (str): Repository slug
            commit_hash (str): Commit hash
            
        Returns:
            dict: Dictionary with additions and deletions
        """
        # For Stash/Bitbucket Server - get diff information
        url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits/{commit_hash}/diff"
        
        # Make the request
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            diff_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching diff for commit {commit_hash[:8]}: {e}")
            return {'additions': 0, 'deletions': 0}
        
        # Calculate additions and deletions
        additions = 0
        deletions = 0
        
        for diff_file in diff_data.get('diffs', []):
            for hunk in diff_file.get('hunks', []):
                for segment in hunk.get('segments', []):
                    if segment.get('type') == 'ADDED':
                        additions += len(segment.get('lines', []))
                    elif segment.get('type') == 'REMOVED':
                        deletions += len(segment.get('lines', []))
        
        return {'additions': additions, 'deletions': deletions}
    
    def find_branch_commits(self, workspace, repo_slug, from_commit, to_commit):
        """
        Find all commits that are in one branch but not in another.
        
        Args:
            workspace (str): Bitbucket workspace/project key
            repo_slug (str): Repository slug
            from_commit (str): Source commit (PR branch)
            to_commit (str): Target commit (main branch)
            
        Returns:
            list: List of commit IDs in the branch
        """
        # For Stash/Bitbucket Server API
        api_url = f"{self.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
        
        # Get the commits from the source branch (PR branch)
        params = {
            'until': from_commit,
            'limit': 100
        }
        
        source_commits = []
        
        while True:
            try:
                response = requests.get(api_url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching source branch commits: {e}")
                return []
            
            source_commits.extend([commit['id'] for commit in data.get('values', [])])
            
            # Check pagination
            is_last_page = data.get('isLastPage', True)
            if is_last_page:
                break
                
            # Update for the next page
            params['start'] = data.get('nextPageStart')
        
        # Get the commits from the target branch (main)
        params = {
            'until': to_commit,
            'limit': 100
        }
        
        target_commits = set()
        
        while True:
            try:
                response = requests.get(api_url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching target branch commits: {e}")
                return []
            
            target_commits.update([commit['id'] for commit in data.get('values', [])])
            
            # Check pagination
            is_last_page = data.get('isLastPage', True)
            if is_last_page:
                break
                
            # Update for the next page
            params['start'] = data.get('nextPageStart')
        
        # Find commits that are in the source branch but not in the target branch
        branch_commits = [commit_id for commit_id in source_commits if commit_id not in target_commits]
        return branch_commits
    
    def analyze_contributions(self, workspace, repo_slug, start_date=None, end_date=None):
        """
        Analyze all contributions (direct commits and PRs) in a repository.
        
        Args:
            workspace (str): Bitbucket workspace/project key
            repo_slug (str): Repository slug
            start_date (datetime): Start date
            end_date (datetime): End date
            
        Returns:
            tuple: Lists of PRs, direct commits, and combined author stats
        """
        # Get all commits in the date range
        all_commits = self.get_all_commits(workspace, repo_slug, start_date, end_date)
        
        if not all_commits:
            print("No commits found in the date range.")
            return [], [], {}
        
        # Step 1: Categorize commits as PR merges or direct commits
        prs = []
        direct_commits = []
        processed_commits = set()
        commit_id_to_pr_map = {}
        
        for commit in all_commits:
            commit_id = commit['id']
            message = commit.get('message', '')
            
            # Check if this is a PR merge commit
            is_pr = "pull request" in message.lower() or "pr #" in message.lower() or "merge pull request" in message.lower()
            
            if is_pr:
                # Extract PR information
                pr_info = self.extract_pr_info(message)
                if pr_info:
                    pr = {
                        "commit": commit,
                        "pr_number": pr_info['number'],
                        "pr_title": pr_info['title'],
                        "author_name": commit.get('author', {}).get('displayName', 'Unknown'),
                        "author_email": commit.get('author', {}).get('emailAddress', 'Unknown'),
                        "direct_changes": {},
                        "associated_commits": [],
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
        
        # Step 2: Analyze each PR merge commit for direct changes
        for pr in prs:
            pr_commit_id = pr['commit']['id']
            stats = self.get_commit_stats(workspace, repo_slug, pr_commit_id)
            pr['direct_changes'] = stats
            pr['total_additions'] += stats.get('additions', 0)
            pr['total_deletions'] += stats.get('deletions', 0)
        
        # Step 3: For each PR, find all its associated commits
        for pr in prs:
            pr_commit = pr['commit']
            pr_commit_id = pr_commit['id']
            
            # Get the PR's parent commits
            parents = pr_commit.get('parents', [])
            if len(parents) >= 2:  # Merge commits typically have 2 parents
                # First parent is usually target branch, second is PR branch
                main_parent_id = parents[0]['id']
                pr_branch_parent_id = parents[1]['id']
                
                # Find all commits in the PR branch but not in the target branch
                branch_commits = self.find_branch_commits(workspace, repo_slug, 
                                                       pr_branch_parent_id, main_parent_id)
                
                # Process each commit in the PR branch
                for commit_id in branch_commits:
                    # Check if this commit is in our original all_commits list
                    matching_commits = [c for c in all_commits if c['id'] == commit_id]
                    if matching_commits:
                        commit = matching_commits[0]
                        
                        # Get commit statistics
                        stats = self.get_commit_stats(workspace, repo_slug, commit_id)
                        
                        # Add to PR's associated commits
                        pr['associated_commits'].append({
                            'id': commit_id,
                            'author_name': commit.get('author', {}).get('displayName', 'Unknown'),
                            'author_email': commit.get('author', {}).get('emailAddress', 'Unknown'),
                            'message': commit.get('message', '').split('\n')[0],  # First line only
                            'date': datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000),
                            'additions': stats.get('additions', 0),
                            'deletions': stats.get('deletions', 0)
                        })
                        
                        # Add to PR's total changes
                        pr['total_additions'] += stats.get('additions', 0)
                        pr['total_deletions'] += stats.get('deletions', 0)
                        
                        # Mark this commit as processed (belongs to a PR)
                        processed_commits.add(commit_id)
        
        # Step 4: Process direct commits (those not part of PRs)
        true_direct_commits = []
        for commit in direct_commits:
            commit_id = commit['id']
            if commit_id not in processed_commits:
                # Get statistics for this direct commit
                stats = self.get_commit_stats(workspace, repo_slug, commit_id)
                
                direct_commit = {
                    'id': commit_id,
                    'author_name': commit.get('author', {}).get('displayName', 'Unknown'),
                    'author_email': commit.get('author', {}).get('emailAddress', 'Unknown'),
                    'message': commit.get('message', '').split('\n')[0],  # First line only
                    'date': datetime.fromtimestamp(commit.get('authorTimestamp', 0) / 1000),
                    'additions': stats.get('additions', 0),
                    'deletions': stats.get('deletions', 0),
                    'total_changes': stats.get('additions', 0) + stats.get('deletions', 0)
                }
                true_direct_commits.append(direct_commit)
        
        # Step 5: Combine all contributions by author
        author_stats = {}
        
        # Add PR contributions
        for pr in prs:
            author_name = pr['author_name']
            author_email = pr['author_email']
            author_key = f"{author_name} <{author_email}>"
            
            if author_key not in author_stats:
                author_stats[author_key] = {
                    'name': author_name,
                    'email': author_email,
                    'pr_count': 0,
                    'pr_commits': 0,
                    'direct_commits': 0,
                    'additions': 0,
                    'deletions': 0,
                    'total_changes': 0
                }
            
            # Update PR counts and changes
            author_stats[author_key]['pr_count'] += 1
            author_stats[author_key]['pr_commits'] += len(pr['associated_commits'])
            author_stats[author_key]['additions'] += pr['total_additions']
            author_stats[author_key]['deletions'] += pr['total_deletions']
            author_stats[author_key]['total_changes'] += pr['total_additions'] + pr['total_deletions']
        
        # Add direct commit contributions
        for commit in true_direct_commits:
            author_name = commit['author_name']
            author_email = commit['author_email']
            author_key = f"{author_name} <{author_email}>"
            
            if author_key not in author_stats:
                author_stats[author_key] = {
                    'name': author_name,
                    'email': author_email,
                    'pr_count': 0,
                    'pr_commits': 0,
                    'direct_commits': 0,
                    'additions': 0,
                    'deletions': 0,
                    'total_changes': 0
                }
            
            # Update direct commit counts and changes
            author_stats[author_key]['direct_commits'] += 1
            author_stats[author_key]['additions'] += commit['additions']
            author_stats[author_key]['deletions'] += commit['deletions']
            author_stats[author_key]['total_changes'] += commit['additions'] + commit['deletions']
        
        return prs, true_direct_commits, author_stats
    
    def save_pr_data(self, prs, filename):
        """
        Save PR data to a CSV file.
        
        Args:
            prs (list): List of PR data
            filename (str): Output filename
        """
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['PR Number', 'Title', 'Author', 'Email', 
                           'Associated Commits', 'Additions', 'Deletions', 'Total Changes'])
            
            for pr in prs:
                writer.writerow([
                    pr['pr_number'],
                    pr['pr_title'],
                    pr['author_name'],
                    pr['author_email'],
                    len(pr['associated_commits']),
                    pr['total_additions'],
                    pr['total_deletions'],
                    pr['total_additions'] + pr['total_deletions']
                ])
    
    def save_direct_commits(self, commits, filename):
        """
        Save direct commit data to a CSV file.
        
        Args:
            commits (list): List of direct commit data
            filename (str): Output filename
        """
        # Group commits by date
        commits_by_date = {}
        for commit in commits:
            date_str = commit['date'].strftime('%Y-%m-%d')
            if date_str not in commits_by_date:
                commits_by_date[date_str] = {
                    'authors': set(),
                    'count': 0,
                    'additions': 0,
                    'deletions': 0
                }
            
            commits_by_date[date_str]['authors'].add(commit['author_name'])
            commits_by_date[date_str]['count'] += 1
            commits_by_date[date_str]['additions'] += commit['additions']
            commits_by_date[date_str]['deletions'] += commit['deletions']
        
        # Write to CSV
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Authors', 'Commit Count', 'Additions', 'Deletions', 'Total Changes'])
            
            for date_str, data in sorted(commits_by_date.items()):
                writer.writerow([
                    date_str,
                    ', '.join(data['authors']),
                    data['count'],
                    data['additions'],
                    data['deletions'],
                    data['additions'] + data['deletions']
                ])
    
    def save_author_stats(self, author_stats, filename):
        """
        Save combined author statistics to a CSV file.
        
        Args:
            author_stats (dict): Author statistics data
            filename (str): Output filename
        """
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Email', 'PRs', 'PR Commits', 'Direct Commits', 
                           'Additions', 'Deletions', 'Total Changes'])
            
            # Sort by total changes descending
            sorted_stats = sorted(
                author_stats.values(), 
                key=lambda x: x['total_changes'], 
                reverse=True
            )
            
            for stats in sorted_stats:
                writer.writerow([
                    stats['name'],
                    stats['email'],
                    stats['pr_count'],
                    stats['pr_commits'],
                    stats['direct_commits'],
                    stats['additions'],
                    stats['deletions'],
                    stats['total_changes']
                ])
    
    def visualize_author_contributions(self, author_stats, workspace, repo_slug):
        """
        Create a visualization of author contributions.
        
        Args:
            author_stats (dict): Author statistics data
            workspace (str): Bitbucket workspace/project key
            repo_slug (str): Repository slug
        """
        # Convert to DataFrame for easier plotting
        stats_list = list(author_stats.values())
        if not stats_list:
            print("No author statistics to visualize")
            return
            
        df = pd.DataFrame(stats_list)
        
        # Sort by total changes and take top 10
        df = df.sort_values('total_changes', ascending=False).head(10)
        
        # Create a stacked bar plot
        plt.figure(figsize=(12, 8))
        
        # Plot additions and deletions
        bars = plt.barh(df['name'], df['additions'], color='green', alpha=0.7, label='Additions')
        plt.barh(df['name'], -df['deletions'], color='red', alpha=0.7, label='Deletions')
        
        # Add numbers to the bars
        for i, bar in enumerate(bars):
            plt.text(
                df['additions'].iloc[i] + 5, 
                bar.get_y() + bar.get_height()/2, 
                f"{int(df['additions'].iloc[i])}", 
                va='center'
            )
            plt.text(
                -df['deletions'].iloc[i] - 50, 
                bar.get_y() + bar.get_height()/2, 
                f"{int(df['deletions'].iloc[i])}", 
                va='center',
                color='white'
            )
        
        # Add PR and direct commit counts
        for i, name in enumerate(df['name']):
            plt.text(
                plt.xlim()[1] * 0.8, 
                i + 0.25, 
                f"PRs: {df['pr_count'].iloc[i]}, Direct: {df['direct_commits'].iloc[i]}",
                va='center',
                fontsize=9
            )
        
        # Customize plot
        plt.title(f'Top Contributors in {workspace}/{repo_slug}')
        plt.xlabel('Lines of Code')
        plt.ylabel('Contributors')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.axvline(x=0, color='black', linewidth=0.5)
        
        # Add summary statistics as text
        total_additions = sum(stats['additions'] for stats in author_stats.values())
        total_deletions = sum(stats['deletions'] for stats in author_stats.values())
        total_changes = total_additions + total_deletions
        plt.figtext(
            0.5, 0.01, 
            f'Total changes: {total_changes} lines (Additions: {total_additions}, Deletions: {total_deletions})', 
            ha='center', 
            fontsize=12, 
            bbox={'facecolor': 'lightgray', 'alpha': 0.5, 'pad': 5}
        )
        
        # Save figure
        plt.tight_layout()
        plt.savefig(f'{workspace}_{repo_slug}_contribution_summary.png', dpi=300, bbox_inches='tight')
        print(f"Visualization saved as '{workspace}_{repo_slug}_contribution_summary.png'")
        
        # Show plot
        plt.show()


def main():
    """Main entry point of the script."""
    parser = argparse.ArgumentParser(description='Analyze Bitbucket repository for both PR and direct commit contributions')
    parser.add_argument('workspace', help='Bitbucket workspace/project (team or user)')
    parser.add_argument('repo_slug', help='Repository slug (name)')
    parser.add_argument('--token', help='Bitbucket access token for Bearer authentication')
    parser.add_argument('--token-file', help='Path to file containing the Bitbucket access token')
    parser.add_argument('--base-url', default='https://stash.arubanetworks.com',
                       help='Base URL for self-hosted Bitbucket/Stash instance')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Get token from file if specified
    token = args.token
    if not token and args.token_file:
        try:
            with open(os.path.expanduser(args.token_file), 'r') as f:
                token = f.read().strip()
        except Exception as e:
            print(f"Error reading token file: {e}")
            return 1
    
    # Use environment variable if still no token
    if not token:
        token = os.environ.get('BITBUCKET_TOKEN')
    
    # Require token for authentication
    if not token:
        print("Error: Bearer token is required for authentication.")
        print("Please provide a token using the --token parameter, --token-file, or set the BITBUCKET_TOKEN environment variable.")
        return 1
    
    # Parse dates if provided
    start_date = None
    end_date = None
    
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        # Default to 14 days ago
        start_date = datetime.now() - timedelta(days=14)
    
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
    else:
        end_date = datetime.now()
    
    print(f"Analyzing contributions from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Create tracker and analyze
    tracker = BitbucketContributionTracker(args.base_url, token)
    prs, direct_commits, author_stats = tracker.analyze_contributions(
        args.workspace, args.repo_slug, start_date, end_date)
    
    # Save results to files
    date_range = f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
    
    # Save PR data
    pr_file = f"all_prs_{date_range}.csv"
    tracker.save_pr_data(prs, pr_file)
    print(f"PR data saved to {pr_file}")
    
    # Save direct commit data
    direct_file = f"direct_commits_{date_range}.csv"
    tracker.save_direct_commits(direct_commits, direct_file)
    print(f"Direct commit data saved to {direct_file}")
    
    # Save author stats
    author_file = f"author_contributions_{date_range}.csv"
    tracker.save_author_stats(author_stats, author_file)
    print(f"Author contribution stats saved to {author_file}")
    
    # Create visualization
    if author_stats:
        tracker.visualize_author_contributions(author_stats, args.workspace, args.repo_slug)
    else:
        print("No author statistics to visualize")
    
    # Print summary
    print("\nContribution Summary:")
    print(f"- Pull Requests: {len(prs)}")
    print(f"- Direct Commits: {len(direct_commits)}")
    print(f"- Contributors: {len(author_stats)}")
    
    # Show top contributors
    if author_stats:
        print("\nTop Contributors:")
        sorted_stats = sorted(
            author_stats.values(), 
            key=lambda x: x['total_changes'], 
            reverse=True
        )
        
        for i, stats in enumerate(sorted_stats[:5], 1):
            print(f"{i}. {stats['name']} - {stats['total_changes']} changes " +
                 f"({stats['pr_count']} PRs, {stats['direct_commits']} direct commits)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
