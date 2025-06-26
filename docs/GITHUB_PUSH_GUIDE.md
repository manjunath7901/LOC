# Pushing to Personal GitHub from Work Laptop

This guide will walk you through using the `push_to_github.sh` script to safely push your code to a personal GitHub repository without affecting your enterprise Git configuration.

## Prerequisites

1. A GitHub account
2. A personal access token from GitHub (classic)
3. Your project code ready to push

## How to Create a Personal Access Token

1. Go to [GitHub Settings > Developer Settings > Personal access tokens](https://github.com/settings/tokens)
2. Click on "Generate new token (classic)"
3. Give your token a name like "LOC Project Access"
4. Select the following scopes:
   - `repo` (Full control of private repositories)
5. Click "Generate token"
6. Copy the token (you will only see it once)

## How to Use the Script

### Option 1: Run the script and enter your token when prompted

```bash
./push_to_github.sh
```

When prompted, paste your personal access token.

### Option 2: Pass your token as an argument

```bash
./push_to_github.sh YOUR_TOKEN
```

Replace `YOUR_TOKEN` with your personal access token.

## What the Script Does

1. **Saves your current Git configuration**: Your enterprise Git settings are saved and will be restored after the push.
2. **Sets repository-specific Git settings**: Temporarily sets your username and email specifically for this push.
3. **Checks for uncommitted changes**: If you have changes that aren't committed, it asks if you want to commit them.
4. **Configures the remote**: Sets up the remote URL with your personal access token.
5. **Pushes to GitHub**: Pushes your code to your personal GitHub repository.
6. **Restores your configuration**: Returns everything back to your original settings.

## Safety Features

- Your token is never stored in the repository
- Your enterprise Git configuration is preserved
- The remote URL is reset after pushing to remove your token
- Original Git user name and email are restored after pushing

## Troubleshooting

If you encounter an error like "remote: Permission denied":
- Make sure your personal access token has the correct permissions
- Verify that you're the owner of the repository or have write access
- Check that your token hasn't expired

## After Pushing

Remember to:
- **Never** share your personal access token
- Set up two-factor authentication on your GitHub account for added security

## Note for Enterprise Security

This script is designed to maintain separation between work and personal GitHub accounts while following security best practices. However, always ensure you're following your company's policies regarding code sharing and external repositories.
