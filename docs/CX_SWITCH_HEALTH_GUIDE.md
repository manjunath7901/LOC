# Analyzing the CX Switch Health Read Assist Repository

This guide provides specific instructions for analyzing the `cx-switch-health-read-assist` repository in the `GVT` project on Stash.

## Prerequisites

1. You need access to the Stash repository at:
   ```
   https://stash.arubanetworks.com/projects/GVT/repos/cx-switch-health-read-assist
   ```

2. You need to have an access token with read permissions for this repository.

## Step 1: Set Up Authentication

Run the `setup_auth.sh` script to securely set up your authentication:

```bash
./setup_auth.sh
```

This script will prompt you for your access token and store it as an environment variable.

## Step 2: Test the Connection

Test that your access token works with:

```bash
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist --test-connection
```

## Step 3: Analyze the Repository

To analyze the repository and group the data by month:

```bash
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist --group-by month
```

### With Additional Options

To filter by specific file extensions (for example, only Python files):

```bash
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist --group-by month --file-extensions .py
```

To ignore merge commits:

```bash
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist --group-by month --ignore-merges
```

To export the data to CSV:

```bash
python bitbucket_loc_analyzer.py GVT cx-switch-health-read-assist --group-by month --export cx_switch_health_loc.csv
```

## Step 4: Using VS Code Task

For convenience, a VS Code task has been created specifically for this repository:

1. Press `Cmd+Shift+P` (or `Ctrl+Shift+P` on Windows)
2. Type "Tasks: Run Task" and select it
3. Choose "Analyze CX Switch Health Read Assist"
4. Enter your access token when prompted

This will analyze the repository, group by month, and export the data to `cx_switch_health_loc.csv`.

## Troubleshooting

If you encounter any issues:

1. Make sure your token has read access to the repository
2. Check if your VPN connection is active (if accessing an internal network)
3. Try the `--test-connection` option to diagnose authentication issues
4. See the TROUBLESHOOTING.md file for more detailed troubleshooting steps
