#!/usr/bin/env python3
"""
Script to analyze individual member contributions in a Bitbucket repository
Focuses on detailed member statistics without graphs
"""

import argparse
import os
import pandas as pd
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer, check_cloc_installation

def main():
    """
    Main function to analyze member contributions in a Bitbucket repository
    """
    parser = argparse.ArgumentParser(description='Analyze individual member contributions in a Bitbucket repository')
    parser.add_argument('workspace', help='Bitbucket workspace/project (team or user)')
    parser.add_argument('repo_slug', help='Repository slug (name)')
    parser.add_argument('--token', help='Bitbucket access token for Bearer authentication')
    parser.add_argument('--base-url', help='Base URL for self-hosted Bitbucket/Stash instance')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--export', help='Export data to CSV file (default: <workspace>_<repo>_member_contributions.csv)')
    parser.add_argument('--file-extensions', nargs='+', 
                        help='Filter by file extensions (e.g., .py .js .tsx)')
    parser.add_argument('--ignore-merges', action='store_true',
                        help='Ignore merge commits')
    parser.add_argument('--include-merges', action='store_true',
                        help='Include merge commits (takes precedence over --ignore-merges)')
    parser.add_argument('--top', type=int, default=0,
                        help='Show only top N contributors (default: show all)')
    parser.add_argument('--sort-by', choices=['commits', 'additions', 'deletions', 'total'], default='total',
                        help='Sort contributors by this metric (default: total changes)')
    parser.add_argument('--detailed', action='store_true',
                        help='Show detailed statistics including impact ratio and avg lines per commit')
    
    args = parser.parse_args()
    
    # Use environment variables if token not provided in command line
    token = args.token if args.token else os.environ.get('BITBUCKET_TOKEN')
    base_url = args.base_url if args.base_url else os.environ.get('BITBUCKET_BASE_URL')
    
    # Require token for authentication
    if not token:
        print("Error: Bearer token is required for authentication.")
        print("Please provide a token using the --token parameter or set the BITBUCKET_TOKEN environment variable.")
        return 1
    
    # Check if cloc is installed
    check_cloc_installation()
    
    # Create analyzer instance
    analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
    
    # Run the analysis with by_user=True to get user statistics
    print(f"Starting analysis of {args.workspace}/{args.repo_slug}...")
    result = analyzer.analyze_repository(
        args.workspace, 
        args.repo_slug, 
        start_date=args.start_date, 
        end_date=args.end_date,
        # Always group by month for the time-based data
        group_by='month',
        file_extensions=args.file_extensions,
        ignore_merges=args.ignore_merges,
        include_merges=args.include_merges,
        # We always want user data
        by_user=True
    )
    
    # Check if analysis returned data
    if result is None:
        print("No data returned from analysis.")
        return 1
    
    # Unpack the result tuple (data, user_df)
    data, user_df = result
    
    if user_df is None or user_df.empty:
        print("No user contribution data available.")
        return 1
    
    # Add additional metrics to the user data
    user_df['total_changes'] = user_df['additions'] + user_df['deletions']
    user_df['net_changes'] = user_df['additions'] - user_df['deletions']
    
    # Calculate additional metrics for detailed view
    if args.detailed:
        # Impact ratio (adds/deletes) - higher means more adding than deleting
        user_df['impact_ratio'] = user_df['additions'] / user_df['deletions'].replace(0, 1)
        user_df['impact_ratio'] = user_df['impact_ratio'].round(2)
        
        # Average lines per commit
        user_df['avg_changes_per_commit'] = (user_df['total_changes'] / user_df['commits']).round(2)
    
    # Determine sort column
    sort_column = {
        'commits': 'commits',
        'additions': 'additions',
        'deletions': 'deletions',
        'total': 'total_changes'
    }.get(args.sort_by, 'total_changes')
    
    # Sort the data
    user_df = user_df.sort_values(by=sort_column, ascending=False)
    
    # Limit to top N if specified
    if args.top > 0:
        user_df = user_df.head(args.top)
    
    # Export to CSV if requested
    if args.export:
        export_path = args.export
        if not export_path.endswith('.csv'):
            export_path += '.csv'
    else:
        export_path = f"{args.workspace}_{args.repo_slug}_member_contributions.csv"
    
    user_df.to_csv(export_path, index=False)
    print(f"\nMember contribution data exported to {export_path}")
    
    # Display repository-wide summary
    total_additions = data['additions'].sum()
    total_deletions = data['deletions'].sum()
    total_changes = total_additions + total_deletions
    
    print("\n== Repository Summary ==")
    print(f"Period: {args.start_date or 'Earliest commit'} to {args.end_date or 'Latest commit'}")
    print(f"Total commits analyzed: {user_df['commits'].sum()}")
    print(f"Total additions: {total_additions:,} lines")
    print(f"Total deletions: {total_deletions:,} lines")
    print(f"Total changes: {total_changes:,} lines")
    print(f"Total contributors: {len(user_df)}")
    
    # Display contributor table
    print("\n== Member Contributions ==")
    print(f"Sorted by: {args.sort_by.capitalize()}")
    
    # Determine columns to display based on detail level
    if args.detailed:
        print("\n| {:<25} | {:>8} | {:>10} | {:>10} | {:>10} | {:>8} | {:>8} |".format(
            "Contributor", "Commits", "Additions", "Deletions", "Total", "Impact", "Avg/Commit"
        ))
        print("|" + "-" * 27 + "|" + "-" * 10 + "|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 10 + "|" + "-" * 10 + "|")
        
        for _, user in user_df.iterrows():
            print("| {:<25} | {:>8} | {:>10,} | {:>10,} | {:>10,} | {:>8} | {:>8} |".format(
                user['name'][:25], 
                int(user['commits']), 
                int(user['additions']), 
                int(user['deletions']), 
                int(user['total_changes']),
                user['impact_ratio'],
                user['avg_changes_per_commit']
            ))
    else:
        print("\n| {:<25} | {:>8} | {:>10} | {:>10} | {:>10} |".format(
            "Contributor", "Commits", "Additions", "Deletions", "Total"
        ))
        print("|" + "-" * 27 + "|" + "-" * 10 + "|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 12 + "|")
        
        for _, user in user_df.iterrows():
            print("| {:<25} | {:>8} | {:>10,} | {:>10,} | {:>10,} |".format(
                user['name'][:25], 
                int(user['commits']), 
                int(user['additions']), 
                int(user['deletions']), 
                int(user['total_changes'])
            ))
    
    # Display percentage contribution for top users
    top_contributors = user_df.head(5)
    total_sum = user_df['total_changes'].sum()
    
    print("\n== Contribution Distribution ==")
    for _, user in top_contributors.iterrows():
        percentage = (user['total_changes'] / total_sum) * 100
        print(f"{user['name'][:25]}: {percentage:.2f}% of all changes")
    
    remaining_percentage = 100 - top_contributors['total_changes'].sum() / total_sum * 100
    if len(user_df) > 5:
        print(f"Other contributors: {remaining_percentage:.2f}% of all changes")
    
    return 0

if __name__ == '__main__':
    exit(main())
