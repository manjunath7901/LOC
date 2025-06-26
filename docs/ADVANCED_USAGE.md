# Advanced Usage Examples for Bitbucket LOC Analyzer

This document provides examples of advanced usage scenarios for the Bitbucket LOC Analyzer tool.

## Testing Connection and Authentication

Before running a full analysis, test your connection and authentication:

```bash
# For Stash/Bitbucket Server
python bitbucket_loc_analyzer.py GVT ui-base \
  --base-url https://stash.arubanetworks.com \
  --token YOUR_ACCESS_TOKEN \
  --test-connection

# For Bitbucket Cloud
python bitbucket_loc_analyzer.py atlassian jira \
  --token YOUR_ACCESS_TOKEN \
  --test-connection
```

## Filtering by File Extensions

Analyze code changes for specific file types:

```bash
# Only JavaScript and TypeScript files
python bitbucket_loc_analyzer.py GVT ui-base \
  --base-url https://stash.arubanetworks.com \
  --token YOUR_ACCESS_TOKEN \
  --file-extensions .js .ts .tsx

# Only Python files from the last 6 months
python bitbucket_loc_analyzer.py GVT ui-base \
  --base-url https://stash.arubanetworks.com \
  --token YOUR_ACCESS_TOKEN \
  --file-extensions .py \
  --start-date $(date -v-6m +%Y-%m-%d)
```

## Ignoring Merge Commits

Focus on actual code changes by ignoring merge commits:

```bash
python bitbucket_loc_analyzer.py GVT ui-base \
  --base-url https://stash.arubanetworks.com \
  --token YOUR_ACCESS_TOKEN \
  --ignore-merges
```

## Complete Example with All Options

Here's a comprehensive example combining multiple options:

```bash
python bitbucket_loc_analyzer.py GVT ui-base \
  --base-url https://stash.arubanetworks.com \
  --token YOUR_ACCESS_TOKEN \
  --start-date 2023-01-01 \
  --end-date 2023-12-31 \
  --group-by month \
  --file-extensions .js .ts .tsx \
  --ignore-merges \
  --export ui-base-js-2023.csv
```

This will:
1. Analyze the `ui-base` repository for the entire year of 2023
2. Only count changes in JavaScript and TypeScript files
3. Ignore merge commits
4. Group results by month
5. Export the data to a CSV file

## Using Environment Variables

Export your credentials as environment variables instead of passing them on the command line:

```bash
export BITBUCKET_TOKEN=your_token
export BITBUCKET_BASE_URL=https://stash.arubanetworks.com

# Then run without authentication parameters
python bitbucket_loc_analyzer.py GVT ui-base \
  --file-extensions .js .ts .tsx
```

## Using VS Code Tasks

The extension also provides VS Code tasks for common operations:

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
2. Type "Run Task" and select "Tasks: Run Task"
3. Select one of:
   - "Run Bitbucket LOC Analyzer"
   - "Test Connection to Bitbucket Server"
   - "Install Requirements"

## Debugging API Issues

For more detailed debug output, modify this value in the `_make_request` method:

```python
# In bitbucket_loc_analyzer.py
def _make_request(self, url, params=None):
    # Set this to True when debugging API issues
    debug_http = True
    
    if debug_http:
        import logging
        from http.client import HTTPConnection
        HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
```
