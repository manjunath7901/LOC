# Bitbucket LOC Analyzer

A Python tool that analyzes Bitbucket repositories to track lines of code added and deleted over time.

## New! Working with HTTP Access Tokens for Stash/Bitbucket Server

For Bitbucket Server (Stash) instances with SSO that require HTTP access tokens, use our improved scripts:

1. Use the `analyze_cx_with_token.sh` script for a one-step solution:
   ```bash
   ./analyze_cx_with_token.sh
   ```
   
   This script:
   - Uses the `fetch_cx_commits.sh` script to obtain commit data
   - Runs the `analyze_cx_final.py` script to analyze commit diffs
   - Generates visualizations and CSV data

2. Or run the components individually:
   ```bash
   # First fetch commits
   ./fetch_cx_commits.sh YOUR_TOKEN
   
   # Then analyze the commits
   python analyze_cx_final.py
   ```

## Features

- Fetch commit data from Bitbucket repositories within a specified date range
- Filter commits by time period (last N days, since/until specific dates)
- Analyze contributions by specific users or email domains
- Generate time-series visualizations of code changes
- Calculate lines added and deleted for each commit
- Group data by day, week, or month
- Visualize code changes with a stacked bar chart
- Export visualization as a PNG file
- Support for HTTP access tokens with Stash/Bitbucket Server

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/bitbucket-loc-analyzer.git
   cd bitbucket-loc-analyzer
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### For Bitbucket Cloud

Basic usage:

```
python bitbucket_loc_analyzer.py workspace repository_slug
```

Example:

```
python bitbucket_loc_analyzer.py atlassian jira
```

### For Self-Hosted Bitbucket/Stash

For Bitbucket Server or Stash, you need to specify the base URL:

```
python bitbucket_loc_analyzer.py PROJECT repository_slug --base-url https://your-stash-instance.com
```

Example for the UI-Base repository:

```
python bitbucket_loc_analyzer.py GVT ui-base --base-url https://stash.arubanetworks.com --token YOUR_ACCESS_TOKEN
```

### Advanced Options

- Specify a date range:
  ```
  python bitbucket_loc_analyzer.py workspace repository_slug --start-date 2023-01-01 --end-date 2023-03-31
  ```

- Group results by day, week, or month:
  ```
  python bitbucket_loc_analyzer.py workspace repository_slug --group-by month
  ```

- Authenticate with username and password:
  ```
  python bitbucket_loc_analyzer.py workspace repository_slug --username YOUR_USERNAME --password YOUR_APP_PASSWORD
  ```

- Authenticate with access token:
  ```
  python bitbucket_loc_analyzer.py workspace repository_slug --token YOUR_BITBUCKET_TOKEN
  ```

- Test connection and authentication without running full analysis:
  ```
  python bitbucket_loc_analyzer.py workspace repository_slug --test-connection
  ```

- Export data to CSV:
  ```
  python bitbucket_loc_analyzer.py workspace repository_slug --export data.csv
  ```

- Filter by file extensions:
  ```
  python bitbucket_loc_analyzer.py workspace repository_slug --file-extensions .py .js .tsx
  ```

- Ignore merge commits:
  ```
  python bitbucket_loc_analyzer.py workspace repository_slug --ignore-merges
  ```

- Set environment variables instead of command-line options:
  ```
  export BITBUCKET_USERNAME=your_username
  export BITBUCKET_PASSWORD=your_password
  # or
  export BITBUCKET_TOKEN=your_token
  export BITBUCKET_BASE_URL=https://your-stash-instance.com
  python bitbucket_loc_analyzer.py workspace repository_slug
  ```

## Output

The tool will:
1. Print a summary of code changes (additions, deletions, net change)
2. Display a visualization of the changes over time
3. Save the visualization as a PNG file in the current directory

## Requirements

- Python 3.6+
- Required packages (installed via requirements.txt):
  - requests
  - pandas
  - matplotlib
  - python-dateutil
  
## Authentication

Bitbucket API requires authentication for most operations. You have three options:

1. **Username and App Password**: Create an app password with read permissions from your Bitbucket account settings
2. **Access Token**: Generate an access token for more secure authentication
3. **Environment Variables**: Set `BITBUCKET_USERNAME` and `BITBUCKET_PASSWORD` or `BITBUCKET_TOKEN`

For self-hosted Bitbucket/Stash instances, you also need to specify the base URL using `--base-url` or the `BITBUCKET_BASE_URL` environment variable.

### Using Access Tokens with SSO

If your organization uses Single Sign-On (SSO) with Stash/Bitbucket Server:

1. Log in to your Stash instance (e.g., https://stash.arubanetworks.com)
2. Go to your user settings (click your profile picture)
3. Select "Personal access tokens" or "HTTP access tokens"
4. Create a new token with repository read permissions
5. Use this token with the `--token` option:

```bash
python bitbucket_loc_analyzer.py GVT repo-name --base-url https://stash.arubanetworks.com --token YOUR_ACCESS_TOKEN
```

## Documentation

For more detailed information, check these guides:

- [HTTP Token Guide](HTTP_TOKEN_GUIDE.md) - How to use HTTP access tokens with Stash/Bitbucket Server
- [User Analysis](USER_ANALYSIS.md) - How to analyze commits by specific users or email domains
- [Time Analysis](TIME_ANALYSIS.md) - How to filter commits by time periods (recent days or specific date ranges)
- [Getting Started](GETTING_STARTED.md) - Quick start guide for new users
- [Advanced Usage](ADVANCED_USAGE.md) - Advanced features and options
- [Troubleshooting](TROUBLESHOOTING.md) - Solutions for common issues

## License

MIT
