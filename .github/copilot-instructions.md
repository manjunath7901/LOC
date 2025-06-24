<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Bitbucket LOC Analyzer Custom Instructions

This is a Python tool that analyzes Bitbucket repositories to track lines of code added and deleted over time.

## Project Structure

- `bitbucket_loc_analyzer.py` - Main script containing the BitbucketLOCAnalyzer class and CLI interface
- `requirements.txt` - Python dependencies for the project

## Key Functionality

The tool:
1. Fetches commit data from Bitbucket repositories
2. Calculates additions and deletions for each commit
3. Groups data by day, week, or month
4. Visualizes changes with matplotlib
5. Provides summary statistics

## Implementation Notes

- Uses the Bitbucket API 2.0 to retrieve commit data
- Requires authentication via username/password or access token
- Implements pagination for repositories with many commits
- For data visualization, green bars represent additions and red bars represent deletions
- Authenticates using either username/password combo or access token
