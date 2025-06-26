# Time-Based LOC Analysis

This guide explains how to use the time-based filtering features of the Bitbucket LOC analyzer to track code changes over specific time periods.

## Prerequisites

1. You must have already fetched the commit data using `fetch_cx_commits.sh`.
2. The commit data should be stored in `cx_commits.json`.

## Timestamp Handling

When filtering commits by date, the tool now uses the **later** timestamp between:
- Author timestamp (when the commit was originally created)
- Committer timestamp (when the commit was merged or applied to the branch)

This ensures that recent merges of older commits are properly included in time-based queries, giving you more accurate data about when code actually entered your branch.

### Why This Matters

Consider this real example from our repository:
- A commit authored on April 17, 2025 but not merged until April 30, 2025
- With the old filtering method (using only author date), this commit would be excluded from a query for "commits in the last 30 days" on June 19, 2025
- With the new method, it's properly included when using the committer date

This is particularly important for workflows where code may be:
1. Created in feature branches and remain there for a while
2. Submitted for code review which takes several days or weeks
3. Finally merged into the main branch much later than the original authoring date

### Benefits of the New Timestamp Approach

- **Newer Merge of Old Commits**: If a commit was authored weeks ago but only merged recently, it will now be included in recent time-based queries based on the merge date.
- **More Accurate Timeline**: The timeline now reflects when code was actually integrated into the codebase, not just when it was written.
- **Better Analysis of Team Activity**: You'll see a more accurate picture of when code was actually reviewed and merged, which is often more important than when it was initially authored.

## Merge Commit Handling

By default, the analyzer excludes merge commits from LOC statistics because they often don't represent original code contributions. However, you can control this behavior:

- `--ignore-merges`: Explicitly exclude merge commits (this is the default behavior)
- `--include-merges`: Include merge commits in the analysis

Including merge commits can be useful when:
- You want to attribute integration work to specific team members
- Your workflow involves substantial work done during merge conflict resolution
- You're analyzing feature branch integration patterns

Note that when using `--include-merges`, the `--ignore-merges` flag is overridden if both are specified.

## Time-Based Filtering Options

You can analyze code changes within specific time periods using the following options:

### Using the Shell Script

```bash
# Analyze all commits from the last 30 days
./analyze_cx_by_user.sh --days=30

# Analyze John's commits from the last 60 days
./analyze_cx_by_user.sh "John Doe" --days=60

# Analyze commits from a specific date range
./analyze_cx_by_user.sh --since=2023-01-01 --until=2023-12-31

# Combine with email domain filtering
./analyze_cx_by_user.sh --email-domain=@example.com --days=90

# List all users who committed in the last 30 days
./analyze_cx_by_user.sh --list-users --days=30

# Include merge commits in the analysis (normally skipped)
./analyze_cx_by_user.sh --days=30 --include-merges

# Explicitly ignore merge commits (this is the default behavior)
./analyze_cx_by_user.sh --days=30 --ignore-merges
```

### Using the Python Script Directly

```bash
# Analyze all commits from the last 30 days
python analyze_cx_by_user.py --days 30

# Analyze a specific user's commits from the last 60 days
python analyze_cx_by_user.py --user "John Doe" --days 60

# Analyze commits from a specific date range
python analyze_cx_by_user.py --since 2023-01-01 --until 2023-12-31 

# Show all users who committed in the last 30 days
python analyze_cx_by_user.py --show-all-users --days 30
```

## How Time-Based Filtering Works

When filtering commits by time period, the analyzer uses the following approach:

1. For each commit, it considers both the **author timestamp** (when the commit was originally written) and the **committer timestamp** (when the commit was actually committed or merged).

2. The analyzer uses the **later** of these two timestamps to determine if a commit falls within the specified time range.

3. This approach ensures that:
   - Recently merged older commits are included in time ranges
   - Commits are counted in the time period when they actually appeared in the branch
   - Both original work and merge/integration work are properly attributed to the right time periods

For example, if a commit was authored one month ago but merged into the main branch yesterday, it will appear in a "last 7 days" report because the merge timestamp is considered.

## Output

The time-based analysis will produce:

1. A CSV file with time-series data grouped by day, week, or month (default: `user_loc_stats.csv`)
2. A summary CSV with totals per user (default: `user_summary_user_loc_stats.csv`)
3. A PNG visualization showing trends over time (default: `user_loc_trends.png`)

The plot title and terminal output will indicate the time range used for the analysis.

## Examples

### Analyzing Recent Changes

To track how much code was changed in the last 30 days:

```bash
./analyze_cx_by_user.sh --days=30
```

### Comparing Activity Between Quarters

To compare code changes between different quarters:

```bash
# Q1 2023
./analyze_cx_by_user.sh --since=2023-01-01 --until=2023-03-31 --output=q1_2023.csv

# Q2 2023
./analyze_cx_by_user.sh --since=2023-04-01 --until=2023-06-30 --output=q2_2023.csv
```

### Finding Most Active Contributors Recently

To identify who has been most active in the codebase recently:

```bash
./analyze_cx_by_user.sh --days=90
```

This will show the top contributors over the last 90 days.
