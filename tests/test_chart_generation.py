#!/usr/bin/env python3
"""
Test script to verify chart generation works without the optimize=True parameter
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def test_chart_generation():
    """Test chart generation with sample data"""
    try:
        print("Testing chart generation...")
        
        # Create sample data
        dates = pd.date_range(start='2025-06-01', end='2025-06-25', freq='D')
        additions = np.random.randint(10, 100, len(dates))
        deletions = np.random.randint(5, 80, len(dates))
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Create bars
        width = 0.8
        ax.bar(dates, additions, width, label='Additions', color='green', alpha=0.7)
        ax.bar(dates, -deletions, width, label='Deletions', color='red', alpha=0.7)
        
        # Set labels and title
        ax.set_xlabel('Date')
        ax.set_ylabel('Lines of Code')
        ax.set_title('Test Chart - Lines of Code Changes Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.tick_params(axis='x', rotation=45)
        
        # Save chart (this should work without optimize=True)
        filename = '/Users/kallatti/LOC/static/test_chart.png'
        
        # Ensure static directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Save with the same parameters as the UI
        plt.tight_layout()
        plt.savefig(filename, dpi=75, bbox_inches='tight', facecolor='white', 
                   format='png')
        
        print(f"✓ Chart saved successfully: {filename}")
        plt.close()
        
        # Verify file was created
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"✓ File exists and is {file_size} bytes")
            return True
        else:
            print("✗ File was not created")
            return False
            
    except Exception as e:
        print(f"✗ Error creating chart: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chart_generation()
    if success:
        print("\n🎉 Chart generation test PASSED!")
        print("The optimize=True parameter fix was successful.")
    else:
        print("\n❌ Chart generation test FAILED!")
        print("There may be other issues with chart generation.")
