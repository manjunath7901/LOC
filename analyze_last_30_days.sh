#!/bin/bash

# Calculate date 30 days ago in YYYY-MM-DD format
START_DATE=$(date -v-30d +"%Y-%m-%d")
END_DATE=$(date +"%Y-%m-%d")

echo "Analyzing from $START_DATE to $END_DATE"

python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist \
  --token "$(cat ~/.bitbucket_token)" \
  --base-url https://stash.arubanetworks.com \
  --start-date $START_DATE \
  --end-date $END_DATE \
  --group-by day \
  --by-user \
  --export last_30_days_stats.csv
