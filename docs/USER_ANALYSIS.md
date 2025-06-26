# User Contribution Analysis for Bitbucket LOC

This tool allows you to analyze code contributions by specific users in a Bitbucket repository.

## Quick Start

1. First, make sure you have the commit data:
   ```
   ./fetch_cx_commits.sh BBDC-Nzg1MjEzMTI1NTA2Or2u0kz+kGNTu2Hstq32TAXa5j/V
   ```

2. To see all users who have committed to the repository:
   ```
   ./analyze_cx_by_user.sh --list-users
   ```

3. To analyze contributions by a specific user:
   ```
   ./analyze_cx_by_user.sh "User Name"
   ```
   
   You can search by:
   - Full name: `"Manjunath Kallatti"`
   - Partial name: `"Manju"`
   - Email: `manjunath.kallatti@hpe.com`

4. To analyze contributions by email domain:
   ```
   ./analyze_cx_by_user.sh --email-domain=@hpe.com
   ```

## Output Files

The tool generates several output files:

1. `user_loc_stats.csv`: Time-series data showing LOC changes by user over time
2. `user_summary_user_loc_stats.csv`: Summary statistics for each user
3. `user_loc_trends.png`: Visualization of code contributions by top users

## Advanced Usage

You can customize the output file name:
```
./analyze_cx_by_user.sh "User Name" --output=custom_filename.csv
```

To get help:
```
./analyze_cx_by_user.sh --help
```

## Sample Analysis

Here's an example of what you can learn:

1. Who are the top contributors by lines of code?
2. What is each user's ratio of additions to deletions?
3. How have contributions patterns changed over time?
4. Who writes the most code in specific time periods?

## Behind the Scenes

This script leverages the Bitbucket API to:

1. Load commit metadata from the pre-fetched `cx_commits.json` file
2. For each commit, fetch the detailed diff from the API
3. Parse the diff to count lines added and deleted
4. Attribute these changes to the commit author
5. Aggregate and visualize the results

The script automatically skips merge commits to avoid counting the same changes multiple times.
