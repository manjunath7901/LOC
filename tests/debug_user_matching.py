#!/usr/bin/env python3
"""
Debug script to test user matching with specific user names.
"""

from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

def debug_user_matching():
    """Debug user matching with specific cases"""
    analyzer = BitbucketLOCAnalyzer(token="dummy_token_for_testing")
    
    # Test with the specific user name from the error
    test_cases = [
        ("Manjunath Kallatti", "Manjunath Kallatti"),
        ("Kallatti, Manjunath", "Manjunath Kallatti"),  # KEY TEST - Reversed format
        ("manjunath.kallatti", "Manjunath Kallatti"),
        ("Manjunath.Kallatti", "Manjunath Kallatti"),
        ("manjunath.kallatti@company.com", "Manjunath Kallatti"),
        ("Manjunath K", "Manjunath Kallatti"),
        ("Manjunath", "Manjunath Kallatti"),
        ("Kallatti", "Manjunath Kallatti"),
        ("manjunath", "Manjunath Kallatti"),
        ("kallatti", "Manjunath Kallatti"),
        ("MANJUNATH KALLATTI", "Manjunath Kallatti"),
        ("KALLATTI, MANJUNATH", "Manjunath Kallatti"),  # KEY TEST - Reversed uppercase
    ]
    
    print("Debugging user matching for 'Manjunath Kallatti':")
    print("=" * 60)
    
    for commit_author, focus_user in test_cases:
        result = analyzer.is_user_match(commit_author, focus_user)
        norm1 = analyzer.normalize_username(commit_author)
        norm2 = analyzer.normalize_username(focus_user)
        
        status = "✓ MATCH" if result else "✗ NO MATCH"
        
        print(f"Author: '{commit_author}' -> normalized: '{norm1}'")
        print(f"Focus:  '{focus_user}' -> normalized: '{norm2}'")
        print(f"Result: {status}")
        print("-" * 40)

if __name__ == "__main__":
    debug_user_matching()
