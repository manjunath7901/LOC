# Bitbucket LOC Analyzer Web UI Guide

This guide explains how to use the web-based interface for the Bitbucket LOC Analyzer.

## Getting Started

1. **Start the Web UI Server**

   First, make sure you have all dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

   Then start the web server:
   ```bash
   python bitbucket_loc_analyzer_ui.py
   ```

   The server will run on http://127.0.0.1:5000 by default.

2. **Access the UI**

   Open a web browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

## Using the Web UI

### Input Form

The web UI provides a simple form where you can enter:

1. **Bitbucket Access Token** - Your personal access token for authentication
2. **Bitbucket Base URL** - The URL of your Bitbucket/Stash instance (default: https://stash.arubanetworks.com)
3. **Workspace/Project Key** - The project or workspace ID (e.g., GVT)
4. **Repository Slug** - The repository name (e.g., cx-switch-health-read-assist)
5. **Date Range** - Start and end dates to analyze
6. **Group By** - Group results by day, week, or month
7. **Analysis Options**:
   - Include PR Analysis - Analyze pull requests
   - Include Direct Commits Analysis - Analyze direct commits

### Results Page

After submitting the form, the UI will show various visualizations and data:

1. **LOC Changes Over Time** - A chart showing additions and deletions over the selected time period
2. **Top Contributors** - A chart showing the top contributors to the repository
3. **Combined Contributor Analysis** - If selected, shows both PR and direct commit contributions
4. **Detailed User Statistics** - A table showing contribution metrics for each user

### Downloading Results

The UI provides download buttons for:
- Daily Stats CSV
- User Stats CSV
- PR Analysis CSV (if selected)
- Direct Commits CSV (if selected)

## Troubleshooting

If you encounter errors:

1. **Authentication Issues**
   - Make sure your Bitbucket token has appropriate permissions
   - For self-hosted instances, ensure the base URL is correct

2. **No Data Returned**
   - Check that the date range contains commits
   - Verify repository name and workspace are correct

3. **Server Not Starting**
   - Make sure Flask is installed: `pip install flask`
   - Check if another service is using port 5000

## Production Deployment

For production environments, it's recommended to:

1. Use a production WSGI server like Gunicorn or uWSGI
2. Set `debug=False` in app.run()
3. Set up proper authentication for the web UI
4. Consider using HTTPS for secure access

Example with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 bitbucket_loc_analyzer_ui:app
```

## Additional Resources

- For advanced usage, see [ADVANCED_USAGE.md](/ADVANCED_USAGE.md)
- For troubleshooting API connections, see [TROUBLESHOOTING.md](/TROUBLESHOOTING.md)
