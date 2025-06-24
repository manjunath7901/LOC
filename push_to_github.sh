#!/bin/bash

# Script to safely push to personal GitHub without affecting enterprise Git settings
# Usage: ./push_to_github.sh [YOUR_TOKEN]
# If token is not provided, you'll be prompted to enter it securely

# Colors for terminal output
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
RED="\033[0;31m"
NC="\033[0m" # No Color

echo -e "${BLUE}=== GitHub Push Helper ===${NC}"
echo -e "${YELLOW}This script will push your local repository to your personal GitHub${NC}"
echo -e "${YELLOW}without affecting your enterprise Git configuration.${NC}"
echo

# Configuration variables - MODIFY THESE
USERNAME="manjunath7901"
REPO="LOC"
GITHUB_EMAIL="manjunathkallatti.is19@bmsce.ac.in"  # Replace with your actual GitHub email
BRANCH="main"

# Store current directory
CURRENT_DIR=$(pwd)

# Verify we're in the right directory
if [[ "$CURRENT_DIR" != *"LOC"* ]]; then
    echo -e "${RED}Error: This script should be run from the LOC directory${NC}"
    exit 1
fi

# Backup current Git config values for this repo
echo -e "${YELLOW}Saving current Git configuration...${NC}"
CURRENT_NAME=$(git config user.name)
CURRENT_EMAIL=$(git config user.email)

# Apply repository-specific Git settings (only affects this repository)
echo -e "${YELLOW}Setting up repository-specific Git configuration...${NC}"
git config user.name "$USERNAME"
git config user.email "$GITHUB_EMAIL"

echo -e "${GREEN}Temporarily set user.name to $USERNAME and user.email to $GITHUB_EMAIL${NC}"
echo -e "${YELLOW}(Your original settings will be restored after push)${NC}"

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}You have uncommitted changes. Do you want to commit them? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}Enter commit message:${NC}"
        read -r commit_msg
        git add .
        git commit -m "$commit_msg"
        echo -e "${GREEN}Changes committed${NC}"
    fi
else
    echo -e "${GREEN}No uncommitted changes detected${NC}"
fi

# Get token - either from command line or by prompting
if [ "$#" -eq 1 ]; then
    TOKEN=$1
else
    echo -e "${YELLOW}Please enter your GitHub Personal Access Token (it won't be stored):${NC}"
    read -rs TOKEN
    echo
fi

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Error: No token provided${NC}"
    exit 1
fi

# Configure the remote URL with authentication temporarily
ORIGINAL_ORIGIN=$(git remote get-url origin 2>/dev/null || echo "")
git remote set-url origin https://${USERNAME}:${TOKEN}@github.com/${USERNAME}/${REPO}.git

# Ensure we're on the main branch
if ! git rev-parse --verify "$BRANCH" &>/dev/null; then
    echo -e "${YELLOW}Branch $BRANCH doesn't exist, creating it...${NC}"
    git checkout -b "$BRANCH"
else
    echo -e "${GREEN}Branch $BRANCH exists${NC}"
    git checkout "$BRANCH"
fi

# Push to GitHub
echo -e "${YELLOW}Pushing to GitHub...${NC}"
git push -u origin "$BRANCH"

# Check if push was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully pushed to GitHub!${NC}"
else
    echo -e "${RED}Push failed. Please check your token and try again.${NC}"
fi

# Restore the original remote URL if it existed
if [ ! -z "$ORIGINAL_ORIGIN" ] && [[ "$ORIGINAL_ORIGIN" != *"${TOKEN}"* ]]; then
    git remote set-url origin "$ORIGINAL_ORIGIN"
    echo -e "${GREEN}Restored original remote URL${NC}"
else
    # Set the URL without the token for safety
    git remote set-url origin https://github.com/${USERNAME}/${REPO}.git
    echo -e "${GREEN}Set remote URL without token${NC}"
fi

# Restore original Git config values
git config user.name "$CURRENT_NAME"
git config user.email "$CURRENT_EMAIL"
echo -e "${GREEN}Restored original Git configuration values${NC}"

echo -e "${BLUE}=== Push Completed ===${NC}"
echo -e "${YELLOW}Remember not to share your personal access token!${NC}"
