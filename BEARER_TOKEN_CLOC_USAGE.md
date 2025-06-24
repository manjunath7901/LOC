# Bitbucket LOC Analyzer with Bearer Token Authentication and CLOC

This guide provides instructions for using Bitbucket Lines of Code (LOC) Analyzer with Bearer token authentication and the CLOC tool for more accurate LOC calculations.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install CLOC

#### macOS
```bash
brew install cloc
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install cloc

# CentOS/RHEL
sudo yum install cloc
```

#### Windows
```bash
# Using Chocolatey
choco install cloc

# Or download from https://github.com/AlDanial/cloc
```

## Using Bearer Token Authentication

This version of the tool uses **only Bearer token authentication** for enhanced security. Basic authentication (username/password) is no longer supported.

### Getting a Bearer Token

1. Log in to your Bitbucket Server/Stash instance
2. Go to your user profile → Personal access tokens
3. Click "Create token"
4. Give it a name and select appropriate permissions (at least repository read access)
5. Save the token in a secure location

## Command Line Usage

### Basic Usage

```bash
python bitbucket_loc_analyzer.py WORKSPACE REPO_SLUG --token YOUR_TOKEN --base-url https://your-bitbucket-instance.com
```

### Full Options

```bash
python bitbucket_loc_analyzer.py WORKSPACE REPO_SLUG \
  --token YOUR_TOKEN \
  --base-url https://your-bitbucket-instance.com \
  --start-date 2023-01-01 \
  --end-date 2023-12-31 \
  --group-by month \
  --file-extensions .py .js .ts \
  --export my_report.csv
```

### Testing Connection

```bash
python bitbucket_loc_analyzer.py WORKSPACE REPO_SLUG --token YOUR_TOKEN --base-url https://your-bitbucket-instance.com --test-connection
```

## Using Environment Variables

You can also set the token and base URL as environment variables:

```bash
export BITBUCKET_TOKEN="your-token"
export BITBUCKET_BASE_URL="https://your-bitbucket-instance.com"

# Then run without specifying token and base-url
python bitbucket_loc_analyzer.py WORKSPACE REPO_SLUG
```

## CLOC Integration Benefits

- More accurate line counting across different file types
- Better handling of whitespace and comments
- Consistent results across different platforms
- Handles complex diffs better than traditional line counting

## Troubleshooting

### CLOC Not Found

If the script cannot find the cloc command, it will fall back to the traditional diff method. Install cloc using the instructions above to get the most accurate LOC statistics.

### Connection Issues

Check that your token has the correct permissions and that the base URL is correct. Use the `--test-connection` flag to diagnose connection issues.
