#!/usr/bin/env python3
"""
Debug script to see what usernames are actually in the repository
"""

from bitbucket_loc_analyzer import BitbucketLOCAnalyzer
import os

def debug_repository_users():
    """Debug what users are actually in the repository"""
    
    # Get token from environment or use a placeholder
    token = os.getenv('BITBUCKET_TOKEN', 'your_token_here')
    base_url = 'https://stash.arubanetworks.com'
    workspace = 'GVT'
    repo_slug = 'cx-switch-device-health'
    
    if token == 'your_token_here':
        print("Please set BITBUCKET_TOKEN environment variable or edit this script")
        return
        
    try:
        analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
        
        print(f"Fetching commits from {workspace}/{repo_slug}...")
        
        # Get recent commits to see what usernames look like
        if analyzer.is_stash:
            url = f"{analyzer.api_base}/rest/api/1.0/projects/{workspace}/repos/{repo_slug}/commits"
        else:
            url = f"{analyzer.api_base}/repositories/{workspace}/{repo_slug}/commits"
            
        params = {'limit': 50}  # Get last 50 commits
        
        response = analyzer._make_request(url, params)
        
        if not response:
            print("Failed to get commits")
            return
            
        commits = response.get('values', [])
        
        print(f"\nFound {len(commits)} recent commits")
        print("=" * 60)
        
        unique_authors = set()
        
        for i, commit in enumerate(commits[:20], 1):  # Show first 20
            if analyzer.is_stash:
                author_name = commit.get('author', {}).get('displayName', 'Unknown')
                author_email = commit.get('author', {}).get('emailAddress', '')
                commit_hash = commit.get('id', '')
            else:
                author_info = commit.get('author', {})
                author_name = author_info.get('user', {}).get('display_name', 'Unknown')
                author_email = author_info.get('raw', '').split('<')[-1].strip('>')
                commit_hash = commit.get('hash', '')
                
            unique_authors.add((author_name, author_email))
            
            print(f"{i:2}. {commit_hash[:8]} | {author_name} | {author_email}")
            
        print("\n" + "=" * 60)
        print("UNIQUE AUTHORS FOUND:")
        print("=" * 60)
        
        for name, email in sorted(unique_authors):
            print(f"Name: '{name}' | Email: '{email}'")
            
            # Test matching with common variations
            test_queries = ['Manjunath', 'Kallatti', 'manjunath', 'kallatti', 'Manjunath Kallatti']
            for query in test_queries:
                if analyzer.is_user_match(name, query):
                    print(f"  -> Matches query: '{query}' ✓")
        
        print(f"\nTotal unique authors: {len(unique_authors)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_repository_users()
