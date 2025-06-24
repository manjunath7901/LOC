# Using HTTP Access Tokens with Bitbucket LOC Analyzer

This guide explains how to use HTTP access tokens with Bitbucket LOC Analyzer for Stash/Bitbucket Server instances with SSO.

## Quick Start Guide

1. **Set up your token**:
   
   You already have your token:
   ```
   BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V
   ```

2. **Run the analysis with one command**:
   ```bash
   ./analyze_cx_with_token.sh
   ```
   
   This will:
   - Fetch all commits from the CX Switch Health Read Assist repository
   - Analyze each commit's diff to calculate line changes
   - Generate visualization and CSV report

3. **View the results**:
   - CSV data: `cx_switch_health_loc.csv`
   - Visualization: `cx_switch_health_loc.png`

## Understanding the Authentication Method

For Stash/Bitbucket Server with HTTP access tokens:

1. The token must be used with the Bearer format:
   ```
   Authorization: Bearer BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V
   ```

2. Other authentication methods (basic auth with token) don't work with your Stash instance.

## Testing Your Token

If you want to test your token directly:

```bash
./test_auth_methods.sh
```

This will show which authentication method works for your token.

## For New Tokens or Users

When your token expires or for new users:

1. Generate a new HTTP access token from Stash/Bitbucket Server
2. Update the token in:
   - `fetch_cx_commits.sh`
   - `analyze_cx_final.py`
   - `analyze_cx_with_token.sh`

## Advanced Usage

If you want to analyze a different repository:

1. Edit the `analyze_cx_final.py` script and modify these variables:
   ```python
   TOKEN = "your-token"
   BASE_URL = "https://stash.arubanetworks.com"
   PROJECT = "project-key"  # e.g., "GVT"
   REPO = "repository-slug"  # e.g., "cx-switch-health-read-assist"
   ```

2. Edit `fetch_cx_commits.sh` to point to your repository:
   ```bash
   PROJECT="your-project-key"
   REPO="your-repository-slug"
   ```

3. Run the analysis as described above.
