#!/usr/bin/env python3
"""
Test script for the user statistics in BitbucketLOCAnalyzer
"""

import pandas as pd
import matplotlib.pyplot as plt
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

def main():
    # Create a test user DataFrame
    user_stats = [
        {
            'name': 'Kallatti, Manjunath',
            'email': 'manjunath.kallatti@hpe.com',
            'commits': 30,
            'additions': 4930,
            'deletions': 647,
            'total_changes': 4930 + 647
        },
        {
            'name': 'Murugan, Sivakumar (HPN)',
            'email': 'sivakumar.murugan@hpe.com',
            'commits': 15,
            'additions': 132,
            'deletions': 9,
            'total_changes': 132 + 9
        },
        {
            'name': 'Murugesan, Sai Navaneetha Ram',
            'email': 'sai.murugesan@hpe.com',
            'commits': 8,
            'additions': 11,
            'deletions': 1,
            'total_changes': 11 + 1
        },
        {
            'name': 'Bhat, Guruprasad K',
            'email': 'guruprasad.bhat@hpe.com',
            'commits': 5,
            'additions': 10,
            'deletions': 8,
            'total_changes': 10 + 8
        }
    ]
    
    user_df = pd.DataFrame(user_stats).sort_values('total_changes', ascending=False)
    
    # Create analyzer instance
    analyzer = BitbucketLOCAnalyzer()
    
    # Test the print_user_statistics method
    analyzer.print_user_statistics(user_df, 'GVT', 'cx-switch-health-read-assist')

if __name__ == "__main__":
    main()
