#!/usr/bin/env python3
"""
Sample data generator for Bitbucket LOC Analyzer
"""

import pandas as pd
from datetime import datetime, timedelta
import random
import os

def generate_sample_data():
    """Generate sample LOC data for testing"""
    
    # Create date range for the past 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Generate dates
    date_range = pd.date_range(start=start_date, end=end_date)
    
    # Create sample data
    data = []
    for date in date_range:
        # Generate random data with some patterns
        if date.weekday() in [5, 6]:  # Weekend
            additions = random.randint(0, 20)
            deletions = random.randint(0, 10)
        else:  # Weekday
            additions = random.randint(20, 150)
            deletions = random.randint(10, 100)
        
        # Add some spikes
        if date.day == 15:
            additions *= 3
            deletions *= 2
        
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'additions': additions,
            'deletions': deletions
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    
    return df

def save_sample_data(group_by='day'):
    """Save sample data to CSV file"""
    
    df = generate_sample_data()
    
    # Group by requested period
    if group_by == 'week':
        df['date'] = df['date'] - pd.to_timedelta(df['date'].dt.dayofweek, unit='D')
        grouped = df.groupby('date').agg({
            'additions': 'sum',
            'deletions': 'sum'
        }).reset_index()
    elif group_by == 'month':
        df['date'] = df['date'].dt.strftime('%Y-%m-01')
        df['date'] = pd.to_datetime(df['date'])
        grouped = df.groupby('date').agg({
            'additions': 'sum',
            'deletions': 'sum'
        }).reset_index()
    else:
        grouped = df
    
    # Save to CSV
    grouped.to_csv('sample_loc_data.csv', index=False)
    print(f"Sample data saved to sample_loc_data.csv (grouped by {group_by})")
    
    return grouped

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # Generate and save sample data
    data = save_sample_data(group_by='week')
    
    # Plot the data
    plt.figure(figsize=(12, 6))
    plt.bar(data['date'], data['additions'], color='green', alpha=0.6, label='Additions')
    plt.bar(data['date'], -data['deletions'], color='red', alpha=0.6, label='Deletions')
    
    plt.title('Sample Code Changes')
    plt.xlabel('Date')
    plt.ylabel('Lines of Code')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.gcf().autofmt_xdate()
    
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
    plt.savefig('sample_loc_changes.png', dpi=300, bbox_inches='tight')
    print("Sample visualization saved as 'sample_loc_changes.png'")
    
    plt.show()
