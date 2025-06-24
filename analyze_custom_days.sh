#!/bin/bash

# Check if days parameter is provided
if [ -z "$1" ]; then
  DAYS=30
else
  DAYS=$1
fi

# Calculate date N days ago in YYYY-MM-DD format
START_DATE=$(date -v-${DAYS}d +"%Y-%m-%d")
END_DATE=$(date +"%Y-%m-%d")

echo "Analyzing last $DAYS days: $START_DATE to $END_DATE"

python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist \
  --token "$(cat ~/.bitbucket_token)" \
  --base-url https://stash.arubanetworks.com \
  --start-date $START_DATE \
  --end-date $END_DATE \
  --group-by day \
  --by-user \
  --export last_${DAYS}_days_stats.csv
