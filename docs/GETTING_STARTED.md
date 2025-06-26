# Getting Started Guide - Bitbucket LOC Analyzer

This guide will help you get started with the Bitbucket LOC Analyzer tool.

## Prerequisites

- Python 3.6 or higher
- A Bitbucket account with access to repositories you want to analyze
- For Bitbucket Server (Stash), an access token or username/password with API access

## Step 1: Set Up Your Environment

1. **Activate the virtual environment**:

   ```bash
   source .venv/bin/activate  # On macOS/Linux
   # OR
   .venv\Scripts\activate     # On Windows
   ```

2. **Install requirements** (if not already installed):

   ```bash
   pip install -r requirements.txt
   ```

## Step 2: Basic Usage

### For Bitbucket Cloud

To analyze a Bitbucket Cloud repository:

```bash
python bitbucket_loc_analyzer.py <workspace> <repository_slug> --group-by month
```

Example:
```bash
python bitbucket_loc_analyzer.py atlassian jira --group-by month
```

### For Bitbucket Server (Stash)

To analyze a Bitbucket Server/Stash repository:

```bash
python bitbucket_loc_analyzer.py <project> <repository_slug> --base-url <server_url> --token <access_token>
```

Example:
```bash
python bitbucket_loc_analyzer.py GVT ui-base --base-url https://stash.arubanetworks.com --token YOUR_ACCESS_TOKEN
```

## Step 3: Testing Your Connection

Before running a full analysis, you can test your connection to the Bitbucket server:

```bash
python bitbucket_loc_analyzer.py <workspace> <repository_slug> --test-connection --base-url <server_url> --token <access_token>
```

## Step 4: Using Advanced Features

### Filter by File Extensions

To only analyze certain file types:

```bash
python bitbucket_loc_analyzer.py <workspace> <repository_slug> --file-extensions .js .ts .tsx
```

### Ignore Merge Commits

To exclude merge commits from the analysis:

```bash
python bitbucket_loc_analyzer.py <workspace> <repository_slug> --ignore-merges
```

### Export Data to CSV

To save the analysis data to a CSV file:

```bash
python bitbucket_loc_analyzer.py <workspace> <repository_slug> --export data.csv
```

### Using Environment Variables

Instead of passing credentials on the command line, you can set environment variables:

```bash
export BITBUCKET_TOKEN=YOUR_TOKEN
export BITBUCKET_BASE_URL=https://stash.example.com
python bitbucket_loc_analyzer.py <workspace> <repository_slug>
```

## Step 5: Using VS Code Tasks

The repository includes VS Code tasks for common operations:

1. Open the Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`)
2. Type "Tasks: Run Task" and select it
3. Choose one of the following tasks:
   - "Run Bitbucket LOC Analyzer"
   - "Test Connection to Bitbucket Server"
   - "Install Requirements"

## Troubleshooting

If you encounter issues:

1. Check your authentication credentials
2. Verify you have proper access to the repository
3. Test the connection using the `--test-connection` flag
4. For more detailed logging, see the debug output in the terminal

For more advanced troubleshooting, refer to TROUBLESHOOTING.md.

## Example with Sample Data

If you want to see how the tool works without connecting to a Bitbucket server, try:

```bash
python sample_data.py
```

This will generate sample LOC data and create a visualization, allowing you to see the output format.
