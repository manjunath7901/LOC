#!/bin/bash

# Calculate date 14 days ago in YYYY-MM-DD format
START_DATE=$(date -v-14d +"%Y-%m-%d")
END_DATE=$(date +"%Y-%m-%d")

echo "Analyzing member contributions from $START_DATE to $END_DATE (last 14 days)"

# Run the Bitbucket LOC analyzer with date filtering for the last 14 days
# The --by-user flag will generate per-user statistics
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist \
  --token "$(cat ~/.bitbucket_token)" \
  --base-url https://stash.arubanetworks.com \
  --start-date $START_DATE \
  --end-date $END_DATE \
  --group-by day \
  --by-user \
  --export last_14days_member_contributions.csv
