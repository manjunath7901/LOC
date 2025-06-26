# Troubleshooting Guide for Bitbucket LOC Analyzer

## Using the Built-in Connection Test

The tool now includes a built-in connection and authentication test feature. Run this first to diagnose issues:

```bash
python bitbucket_loc_analyzer.py GVT ui-base \
  --base-url https://stash.arubanetworks.com \
  --token YOUR_ACCESS_TOKEN \
  --test-connection
```

This will test:
1. Basic connectivity to the Bitbucket server
2. API endpoint accessibility
3. Repository access permissions

## Connection Issue: Failed to resolve 'stash.arubanetworks.com'

Based on the error message in the terminal, we have a DNS resolution issue. Here's how to troubleshoot:

### 1. Check DNS Resolution

```bash
# Check if your machine can resolve the hostname
ping stash.arubanetworks.com
```

If this fails, you might need to:
- Check your VPN connection if it's an internal server
- Add the hostname to your /etc/hosts file
- Use an IP address directly instead of the hostname

### 2. Check Connectivity

```bash
# Try with curl to test basic connectivity
curl -v https://stash.arubanetworks.com
```

### 3. Authentication Methods

Stash/Bitbucket Server supports several authentication methods:

#### a. Basic Authentication with Username/Password

```bash
python bitbucket_loc_analyzer.py GVT ui-base --base-url https://stash.arubanetworks.com --username YOUR_USERNAME --password YOUR_PASSWORD
```

#### b. Access Token Authentication

For Stash/Bitbucket Server, try with these formats:

```bash
# As a personal access token
python bitbucket_loc_analyzer.py GVT ui-base --base-url https://stash.arubanetworks.com --token YOUR_TOKEN

# With Bearer prefix
export BITBUCKET_TOKEN="Bearer YOUR_TOKEN"
python bitbucket_loc_analyzer.py GVT ui-base --base-url https://stash.arubanetworks.com
```

### 4. API URL Format

Stash/Bitbucket Server API paths can vary by version:

- Modern Bitbucket Server: `/rest/api/1.0/projects/GVT/repos/ui-base/commits`
- Older versions might use different paths

### 5. Code Modifications for Testing

You can modify the code to debug specific issues:

#### Disable SSL Verification (For Testing Only)

In the `_make_request` method, change `verify = True` to `verify = False`

#### Add More Debug Output

Uncomment and use this code to see detailed request/response:

```python
import logging
from http.client import HTTPConnection
HTTPConnection.debuglevel = 1
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```

### 6. Check API Endpoint Directly

Use a tool like Postman or curl to test the API directly:

```bash
curl -u username:password https://stash.arubanetworks.com/rest/api/1.0/projects/GVT/repos/ui-base/commits
```

### 7. Known Issues with Stash/Bitbucket Server

- Date format: Some Stash versions require different date formats
- Token format: Some versions require different authentication header formats
- API paths: Differences between versions

### Remember

For security, never add your actual token or password in the script. Use environment variables or command-line flags.
