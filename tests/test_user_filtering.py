#!/usr/bin/env python3
"""
Test script to verify user filtering improvements work correctly.
"""

from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

def test_user_matching():
    """Test the is_user_match function with various scenarios"""
    # Create analyzer with dummy token for testing
    analyzer = BitbucketLOCAnalyzer(token="dummy_token_for_testing")
    
    # Test cases: (commit_author, focus_user, expected_result)
    test_cases = [
        # Exact matches
        ("John Doe", "John Doe", True),
        ("john.doe", "John Doe", True),
        ("JOHN DOE", "john doe", True),
        
        # Reversed name format - THE KEY TEST CASE!
        ("Kallatti, Manjunath", "Manjunath Kallatti", True),
        ("Manjunath Kallatti", "Kallatti, Manjunath", True),
        ("Smith, John", "John Smith", True),
        ("Doe, Jane", "Jane Doe", True),
        
        # Email matches
        ("john.doe@company.com", "john.doe", True),
        ("john.doe@company.com", "john", True),
        
        # Substring matches that should work
        ("John Smith", "John", True),
        ("Robert Johnson", "Robert", True),
        ("manjunath.kallatti", "manjunath", True),
        
        # Substring matches that should NOT work (too short/generic)
        ("Daniel Anderson", "an", False),
        ("Daniel Anderson", "da", False),
        ("Samuel Adams", "am", False),
        
        # Matches that should work (meaningful substrings)
        ("Daniel Anderson", "Daniel", True),
        ("Daniel Anderson", "Anderson", True),
        ("Samuel Adams", "Samuel", True),
        ("Samuel Adams", "Adams", True),
        
        # Complex name variations
        ("Kallatti, Manjunath K", "Manjunath Kallatti", True),
        ("Dr. John Smith", "John Smith", True),
        ("Smith Jr., John", "John Smith", True),
        
        # No matches
        ("John Doe", "Jane Smith", False),
        ("Alice Johnson", "Bob Wilson", False),
        
        # Edge cases
        ("", "John", False),
        ("John", "", False),
        ("", "", False),
        (None, "John", False),
        ("John", None, False),
    ]
    
    print("Testing user matching logic:")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for commit_author, focus_user, expected in test_cases:
        result = analyzer.is_user_match(commit_author, focus_user)
        status = "PASS" if result == expected else "FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status:4} | '{commit_author}' vs '{focus_user}' -> {result} (expected: {expected})")
    
    print("=" * 50)
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    print(f"Success rate: {passed/(passed+failed)*100:.1f}%")
    
    return failed == 0

if __name__ == "__main__":
    success = test_user_matching()
    print(f"\nOverall test result: {'SUCCESS' if success else 'FAILURE'}")
