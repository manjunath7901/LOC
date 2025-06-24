# Bitbucket LOC Analyzer Usage Example

## Analyzing the UI-Base Repository

To analyze the UI-Base repository in the GVT project from Stash, use the following command:

```bash
python bitbucket_loc_analyzer.py GVT ui-base \
  --base-url https://stash.arubanetworks.com \
  --token YOUR_ACCESS_TOKEN \
  --start-date 2025-01-01 \
  --group-by month
```

## Steps to Get an Access Token

1. Log in to [Stash](https://stash.arubanetworks.com)
2. Click your profile picture in the top right corner
3. Select "Manage account"
4. Go to "Personal access tokens"
5. Click "Create token"
6. Set the following:
   - Name: LOC Analyzer
   - Permissions: Make sure "Repository read" is selected
   - Expiration: Choose an appropriate date
7. Click "Create" and copy the generated token
8. Use this token with the `--token` parameter in the command

## Troubleshooting

If you encounter SSL certificate issues, you may need to disable SSL verification temporarily by modifying the code:

1. Open `bitbucket_loc_analyzer.py`
2. Find the line with `verify = True` in the `_make_request` method
3. Change it to `verify = False`
4. Note: This is not recommended for security-sensitive environments

## Environment Variables

Instead of passing the token on the command line, you can set environment variables:

```bash
export BITBUCKET_TOKEN=YOUR_ACCESS_TOKEN
export BITBUCKET_BASE_URL=https://stash.arubanetworks.com
python bitbucket_loc_analyzer.py GVT ui-base
```
