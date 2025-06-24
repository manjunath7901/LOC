#!/usr/bin/env python3
import pandas as pd

# Read the CSV files
standard_loc = pd.read_csv('standard_loc_last_14days.csv')
user_stats = pd.read_csv('GVT_cx-switch-health-read-assist_user_stats.csv')
author_contrib = pd.read_csv('author_contributions_20250610_to_20250624.csv')

print("STANDARD LOC DATA BY DATE:")
print(standard_loc)
print("\nUSER STATS:")
print(user_stats)
print("\nAUTHOR CONTRIBUTIONS:")
print(author_contrib)

# Compare Kallatti's stats
kallatti_user_stats = user_stats[user_stats['name'] == 'Kallatti, Manjunath']
kallatti_author_contrib = author_contrib[author_contrib['Name'] == 'Kallatti, Manjunath']

print("\nKallatti stats from standard LOC:")
if not kallatti_user_stats.empty:
    print(f"Additions: {kallatti_user_stats.iloc[0]['additions']}")
    print(f"Deletions: {kallatti_user_stats.iloc[0]['deletions']}")
    print(f"Total changes: {kallatti_user_stats.iloc[0]['total_changes']}")
else:
    print("No data found")

print("\nKallatti stats from author contributions:")
if not kallatti_author_contrib.empty:
    print(f"Additions: {kallatti_author_contrib.iloc[0]['Additions']}")
    print(f"Deletions: {kallatti_author_contrib.iloc[0]['Deletions']}")
    print(f"Total changes: {kallatti_author_contrib.iloc[0]['Total Changes']}")
else:
    print("No data found")
