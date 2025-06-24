# Contribution Analysis Guide

This guide explains how to accurately track user contributions in Bitbucket repositories.

## The Problem

When analyzing contributions in Bitbucket repositories, there are two types of contributions that need to be tracked:

1. **Pull Request (PR) based changes** - Code changes that are submitted via pull requests
2. **Direct commit changes** - Code changes that are pushed directly to the repository

The standard PR-based analysis can undercount contributions because it only tracks PR merges, not direct commits. The discrepancy can be significant for users who frequently make direct commits to the repository.

## Solution: Combined Analysis Approach

We've created a comprehensive solution that accurately tracks both types of contributions:

### 1. Standard LOC Analysis

The standard LOC analysis (`bitbucket_loc_analyzer.py`) counts all lines of code changes, regardless of how they were contributed:

```bash
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist \
  --token "$(cat ~/.bitbucket_token)" \
  --start-date 2023-06-10 \
  --end-date 2023-06-24 \
  --group-by day \
  --by-user
```

### 2. Comprehensive PR+Direct Analysis

Our new tool (`analyze_direct_and_pr_contributions.py`) provides a complete breakdown of contributions:

```bash
python analyze_direct_and_pr_contributions.py GVT cx-switch-health-read-assist \
  --token-file ~/.bitbucket_token \
  --start-date 2023-06-10 \
  --end-date 2023-06-24
```

This tool:
- Identifies PR merge commits and their associated changes
- Tracks direct commits separately
- Combines both types for accurate contribution reporting
- Visualizes the results with detailed breakdown by contributor

### 3. Quick Analysis Script

For convenience, use the `analyze_contributions.sh` script to run both analyses for the last 14 days:

```bash
./analyze_contributions.sh
```

## Understanding the Output

The comprehensive analysis generates several files:

- `all_prs_YYYYMMDD_to_YYYYMMDD.csv` - List of all PRs with their changes
- `direct_commits_YYYYMMDD_to_YYYYMMDD.csv` - Direct commits grouped by date
- `author_contributions_YYYYMMDD_to_YYYYMMDD.csv` - Complete author statistics
- `GVT_cx-switch-health-read-assist_contribution_summary.png` - Visualization of top contributors

The standard analysis generates:
- `standard_loc_last_14days.csv` - LOC changes by date
- `GVT_cx-switch-health-read-assist_user_stats.csv` - User statistics

## Example Case Study

In a recent analysis of the cx-switch-health-read-assist repository:

- **Standard LOC Analysis**: Showed that Manjunath Kallatti had contributed 43 additions and 10 deletions (53 total changes)
- **PR-based Analysis**: Showed only 2 changes for the same user
- **Combined Analysis**: Confirmed that Manjunath had made several direct commits on June 12 that were not tied to PRs

The comprehensive analysis properly attributed all 53 changes to Manjunath, matching the standard LOC analysis results.

## Conclusion

Always use the comprehensive analysis approach for accurate contribution reporting, especially when both PRs and direct commits are used in your workflow.
