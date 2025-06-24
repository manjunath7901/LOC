#!/usr/bin/env python3
"""
Complete test script for the BitbucketLOCAnalyzer with the updated user statistics
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

def main():
    # Create mock analyzer
    analyzer = BitbucketLOCAnalyzer()
    
    # Create mock repository data
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 6, 1)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    repo_data = []
    for date in dates:
        # Generate random data
        if date.weekday() < 5:  # Weekday
            additions = random.randint(20, 200)
            deletions = random.randint(10, 100)
        else:  # Weekend
            additions = random.randint(5, 50) 
            deletions = random.randint(0, 20)
            
        repo_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'additions': additions,
            'deletions': deletions
        })
    
    repo_df = pd.DataFrame(repo_data)
    repo_df['date'] = pd.to_datetime(repo_df['date'])
    
    # Group data by month
    repo_df['month'] = repo_df['date'].dt.strftime('%Y-%m')
    monthly_data = repo_df.groupby('month').agg({
        'additions': 'sum',
        'deletions': 'sum'
    }).reset_index()
    monthly_data['date'] = pd.to_datetime(monthly_data['month'] + '-01')
    
    # Create user statistics
    user_stats = [
        {
            'name': 'Kallatti, Manjunath',
            'email': 'manjunath.kallatti@example.com',
            'commits': 30,
            'additions': 4930,
            'deletions': 647,
            'total_changes': 4930 + 647
        },
        {
            'name': 'Murugan, Sivakumar (HPN)',
            'email': 'sivakumar.murugan@example.com', 
            'commits': 15,
            'additions': 132,
            'deletions': 9,
            'total_changes': 132 + 9
        },
        {
            'name': 'Murugesan, Sai Navaneetha Ram',
            'email': 'sai.murugesan@example.com',
            'commits': 8,
            'additions': 11,
            'deletions': 1,
            'total_changes': 11 + 1
        },
        {
            'name': 'Bhat, Guruprasad K',
            'email': 'guruprasad.bhat@example.com',
            'commits': 5,
            'additions': 10,
            'deletions': 8,
            'total_changes': 10 + 8
        }
    ]
    
    user_df = pd.DataFrame(user_stats).sort_values('total_changes', ascending=False)
    
    # Create custom visualization for monthly data
    plt.figure(figsize=(12, 6))
    plt.bar(monthly_data['date'], monthly_data['additions'], color='green', alpha=0.7, label='Additions')
    plt.bar(monthly_data['date'], -monthly_data['deletions'], color='red', alpha=0.7, label='Deletions')
    plt.title('Monthly Code Changes')
    plt.xlabel('Month')
    plt.ylabel('Lines of Code')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('test_monthly_changes.png', dpi=300, bbox_inches='tight')
    print("\nMonthly changes visualization saved as 'test_monthly_changes.png'")
    
    # Test user statistics
    print("\nTesting user statistics...")
    analyzer.print_user_statistics(user_df, 'TEST', 'repository')
    
    # Print overall summary
    print("\nCode changes summary:")
    total_additions = monthly_data['additions'].sum()
    total_deletions = monthly_data['deletions'].sum()
    total_changes = total_additions + total_deletions
    print(f"Total additions: {total_additions} lines")
    print(f"Total deletions: {total_deletions} lines")
    print(f"Total changes: {total_changes} lines (sum of additions and deletions)")
    
    print("\nAll tests completed. Please check output files.")

if __name__ == "__main__":
    main()
