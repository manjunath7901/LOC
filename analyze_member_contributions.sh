#!/bin/bash
# Script to analyze member contributions in a Bitbucket repository

# Check if token is provided
if [ -z "$1" ]; then
    echo "Please provide a token as the first argument"
    echo "Usage: $0 YOUR_TOKEN [WORKSPACE] [REPO_SLUG]"
    exit 1
fi

TOKEN="$1"
WORKSPACE="${2:-GVT}"
REPO_SLUG="${3:-cx-switch-health-read-assist}"
BASE_URL="https://stash.arubanetworks.com"
START_DATE="2023-01-01"
END_DATE=$(date +%Y-%m-%d)
EXPORT="${WORKSPACE}_${REPO_SLUG}_member_contributions.csv"

echo "Analyzing member contributions for $WORKSPACE/$REPO_SLUG..."
echo "Using token: ${TOKEN:0:5}..."
echo "Date range: $START_DATE to $END_DATE"
echo ""

# Run the analysis
python member_contributions.py "$WORKSPACE" "$REPO_SLUG" \
    --token "Bearer $TOKEN" \
    --base-url "$BASE_URL" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --export "$EXPORT" \
    --detailed

# Check exit code
if [ $? -ne 0 ]; then
    echo "Error running the analysis"
    exit 1
fi

echo ""
echo "Analysis completed successfully"
echo "Results exported to $EXPORT"
