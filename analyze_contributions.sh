#!/bin/bash

# Calculate date 14 days ago in YYYY-MM-DD format
START_DATE=$(date -v-14d +"%Y-%m-%d")
END_DATE=$(date +"%Y-%m-%d")

echo "Analyzing member contributions from $START_DATE to $END_DATE (last 14 days)"

# Check for token file
TOKEN_FILE=~/.bitbucket_token
if [ ! -f "$TOKEN_FILE" ]; then
  echo "Error: Token file not found at $TOKEN_FILE"
  echo "Please create this file with your Bitbucket token"
  exit 1
fi

# Run the new comprehensive contribution analyzer
python analyze_direct_and_pr_contributions.py GVT cx-switch-health-read-assist \
  --token-file ~/.bitbucket_token \
  --start-date $START_DATE \
  --end-date $END_DATE

# Also run the standard LOC analyzer for comparison
echo -e "\nRunning standard LOC analysis for comparison..."
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist \
  --token "$(cat ~/.bitbucket_token)" \
  --base-url https://stash.arubanetworks.com \
  --start-date $START_DATE \
  --end-date $END_DATE \
  --group-by day \
  --by-user \
  --export standard_loc_last_14days.csv

echo
echo "======================= FINAL RESULTS ======================="
echo "Standard LOC analysis results:"
echo "  - CSV: standard_loc_last_14days.csv"
echo "  - User stats: GVT_cx-switch-health-read-assist_user_stats.csv"
echo
echo "Comprehensive PR+Direct analysis results:"
echo "  - All PRs: all_prs_${START_DATE//-/}_to_${END_DATE//-/}.csv"
echo "  - Direct commits: direct_commits_${START_DATE//-/}_to_${END_DATE//-/}.csv"
echo "  - Author contributions: author_contributions_${START_DATE//-/}_to_${END_DATE//-/}.csv"
echo "  - Visualization: GVT_cx-switch-health-read-assist_contribution_summary.png"
echo
echo "The comprehensive analysis provides a complete picture of contributions"
echo "by accurately attributing both PR-based and direct commit changes."
echo "============================================================"
