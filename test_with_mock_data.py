#!/usr/bin/env python3
"""
Test script for the BitbucketLOCAnalyzer with mock data
"""

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

def main():
    # Create a mock analyzer
    analyzer = BitbucketLOCAnalyzer()
    
    # Mock data for the repository analysis
    # Create date range for past 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create mock data for overall repository stats
    data = []
    for date in date_range:
        # Generate random data with some patterns
        if date.weekday() in [5, 6]:  # Weekend
            additions = random.randint(0, 20)
            deletions = random.randint(0, 10)
        else:  # Weekday
            additions = random.randint(20, 150)
            deletions = random.randint(10, 100)
            
        data.append({
            'date': date.strftime('%Y-%m-%d'),  # Convert to string to match expected format
            'additions': additions,
            'deletions': deletions
        })
    
    # Create DataFrame
    grouped_df = pd.DataFrame(data)
    
    # Convert date back to datetime for proper plotting
    grouped_df['date'] = pd.to_datetime(grouped_df['date'])
    
    # Create mock user data
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
    
    # Simulate overall statistics
    print("\nCode changes summary:")
    total_additions = grouped_df['additions'].sum()
    total_deletions = grouped_df['deletions'].sum()
    total_changes = total_additions + total_deletions
    print(f"Total additions: {total_additions} lines")
    print(f"Total deletions: {total_deletions} lines")
    print(f"Total changes: {total_changes} lines (sum of additions and deletions)")
    
    # Modify visualize_changes to not show the plot interactively
    workspace = 'GVT'
    repo_slug = 'cx-switch-health-read-assist'
    
    # Group by month for visualization
    grouped_df['month'] = grouped_df['date'].dt.strftime('%Y-%m')
    monthly_data = grouped_df.groupby('month').agg({
        'additions': 'sum',
        'deletions': 'sum'
    }).reset_index()
    monthly_data['date'] = pd.to_datetime(monthly_data['month'] + '-01')
    
    # Call visualize_changes after patching it to not show plots interactively
    plt.switch_backend('Agg')
    
    # Testing user statistics visualization
    print("\nTesting user statistics...")
    analyzer.print_user_statistics(user_df, workspace, repo_slug)
    
    print("\nDone! Check the generated PNG files for visualizations.")

if __name__ == "__main__":
    main()
