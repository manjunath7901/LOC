#!/usr/bin/env python3
"""
Bitbucket LOC Analyzer Web UI

This script creates a web interface for analyzing Bitbucket repository contributions,
allowing users to input token, repository details, and time range.
"""

from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import tempfile
import datetime
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import time
matplotlib.use('Agg')  # Use non-interactive backend for server environments

current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, 
            static_folder=static_folder,
            static_url_path='/static')

print(f"Using static folder path: {static_folder}")

# Ensure directories exist
os.makedirs('static', exist_ok=True)
os.makedirs('static/images', exist_ok=True)
os.makedirs('static/data', exist_ok=True)

# Ensure proper permissions for the static directories
try:
    import stat
    os.chmod('static', stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod('static/images', stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.chmod('static/data', stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
except Exception as e:
    print(f"Warning: Could not set directory permissions: {e}")
    
# Clear any old files from static directories
for file in os.listdir('static/images'):
    if file.endswith('.png'):
        try:
            os.remove(os.path.join('static/images', file))
            print(f"Removed old file: static/images/{file}")
        except Exception as e:
            print(f"Could not remove file {file}: {e}")
            
for file in os.listdir('static/data'):
    if file.endswith('.csv'):
        try:
            os.remove(os.path.join('static/data', file))
            print(f"Removed old file: static/data/{file}")
        except Exception as e:
            print(f"Could not remove file {file}: {e}")

@app.route('/')
def index():
    """Render the main page with the form"""
    # Get current date and 14 days ago for default values
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    two_weeks_ago = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime('%Y-%m-%d')
    
    return render_template('index.html', 
                          today=today, 
                          two_weeks_ago=two_weeks_ago)

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process the form data and run the analysis"""
    # Get form data
    token = request.form.get('token', '')
    base_url = request.form.get('base_url', 'https://stash.arubanetworks.com')
    workspace = request.form.get('workspace', '')
    repo_slug = request.form.get('repo_slug', '')
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    group_by = request.form.get('group_by', 'day')
    include_prs = 'include_prs' in request.form
    include_direct = 'include_direct' in request.form
    
    # Generate unique ID for this analysis
    analysis_id = f"{workspace}_{repo_slug}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # File paths for output
    user_stats_file = f"static/data/{analysis_id}_user_stats.csv"
    daily_stats_file = f"static/data/{analysis_id}_daily_stats.csv"
    chart_file = f"static/images/{analysis_id}_chart.png"
    user_chart_file = f"static/images/{analysis_id}_user_chart.png"
    
    # Run standard LOC analysis
    try:
        analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
        print(f"Starting repository analysis for {workspace}/{repo_slug}...")
        
        results = analyzer.analyze_repository(
            workspace, 
            repo_slug,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            by_user=True
        )
        
        print(f"Analysis completed, returned results type: {type(results)}")
        if results is None:
            return render_template('error.html', 
                                message="Analysis returned None. Please check your parameters and try again.")
        
        if isinstance(results, tuple) and len(results) < 2:
            print(f"Warning: Expected at least 2 DataFrames, but got {len(results)}")
            return render_template('error.html', 
                                message="Analysis returned incomplete data. Please check your parameters and try again.")
        
        # Unpack results
        daily_data, user_data = results
        
        # Save data to CSV
        daily_data.to_csv(daily_stats_file, index=False)
        user_data.to_csv(user_stats_file, index=False)
        
        # Generate charts
        # LOC changes over time
        plt.figure(figsize=(10, 6))
        plt.bar(daily_data['date'], daily_data['additions'], color='green', alpha=0.6, label='Additions')
        plt.bar(daily_data['date'], -daily_data['deletions'], color='red', alpha=0.6, label='Deletions')
        plt.title(f'Code Changes in {workspace}/{repo_slug}')
        plt.xlabel(f'Date (grouped by {group_by})')
        plt.ylabel('Lines of Code')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        plt.savefig(chart_file, dpi=300)
        plt.close()
        
        # User contribution chart
        plt.figure(figsize=(12, 6))
        top_users = user_data.sort_values('total_changes', ascending=False).head(10)
        plt.bar(top_users['name'], top_users['additions'], color='green', alpha=0.6, label='Additions')
        plt.bar(top_users['name'], -top_users['deletions'], color='red', alpha=0.6, label='Deletions', bottom=0)
        plt.title(f'Top Contributors in {workspace}/{repo_slug}')
        plt.xlabel('Users')
        plt.ylabel('Lines of Code')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(user_chart_file, dpi=300)
        plt.close()
        
        # If direct commits analysis is selected, run additional analysis
        direct_commits_file = None
        pr_analysis_file = None
        combined_chart_file = None
        
        if include_direct or include_prs:
            # Create a more comprehensive analysis
            from analyze_direct_and_pr_contributions import BitbucketContributionTracker
            
            tracker = BitbucketContributionTracker(base_url, token)
            start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            
            # Run the comprehensive analysis
            prs, direct_commits, author_stats = tracker.analyze_contributions(
                workspace, repo_slug, start_dt, end_dt
            )
            
            # Save PR and direct commit data if requested
            if include_prs:
                pr_analysis_file = f"static/data/{analysis_id}_prs.csv"
                with open(pr_analysis_file, 'w', newline='') as f:
                    import csv
                    writer = csv.writer(f)
                    writer.writerow(['PR Number', 'Title', 'Author', 'Additions', 'Deletions', 'Total'])
                    for pr in prs:
                        writer.writerow([
                            pr.get('pr_number', 'N/A'),
                            pr.get('pr_title', 'N/A'),
                            pr.get('author_name', 'Unknown'),
                            pr.get('total_additions', 0),
                            pr.get('total_deletions', 0),
                            pr.get('total_additions', 0) + pr.get('total_deletions', 0)
                        ])
            
            if include_direct:
                direct_commits_file = f"static/data/{analysis_id}_direct_commits.csv"
                with open(direct_commits_file, 'w', newline='') as f:
                    import csv
                    writer = csv.writer(f)
                    writer.writerow(['Date', 'Author', 'Message', 'Additions', 'Deletions', 'Total'])
                    for commit in direct_commits:
                        date_str = commit.get('date', datetime.datetime.now()).strftime('%Y-%m-%d')
                        writer.writerow([
                            date_str,
                            commit.get('author_name', 'Unknown'),
                            commit.get('message', 'N/A')[:50],
                            commit.get('additions', 0),
                            commit.get('deletions', 0),
                            commit.get('additions', 0) + commit.get('deletions', 0)
                        ])
            
            # Create combined chart
            combined_chart_file = f"static/images/{analysis_id}_combined_chart.png"
            if author_stats:
                plt.figure(figsize=(14, 10))  # Larger figure for better readability
                df = pd.DataFrame([
                    {
                        'name': stats['name'],
                        'additions': stats['additions'],
                        'deletions': stats['deletions'],
                        'total_changes': stats['additions'] + stats['deletions'],
                        'pr_count': stats.get('pr_count', 0),
                        'direct_commits': stats.get('direct_commits', 0)
                    } 
                    for stats in author_stats.values()
                ])
                # Sort by total activity (additions + deletions) to get most active contributors
                df = df.sort_values('total_changes', ascending=False).head(10)
                
                # The y-position for each author
                y_pos = range(len(df['name']))
                
                # Create horizontal bar chart with more space between bars
                bars_add = plt.barh(y_pos, df['additions'], color='green', alpha=0.7, label='Additions', height=0.4)
                bars_del = plt.barh(y_pos, -df['deletions'], color='red', alpha=0.7, label='Deletions', height=0.4)
                
                # Calculate maximum values for axis scaling and text positioning
                max_add = df['additions'].max()
                max_del = df['deletions'].max()
                max_val = max(max_add, max_del) * 1.3  # Add 30% margin
                
                # Add PR and direct commit counts
                for i, (_, row) in enumerate(df.iterrows()):
                    # Position text on the right side of additions bar with proper offset
                    plt.text(
                        max_add + (max_val * 0.05),
                        i,
                        f"PRs: {row['pr_count']}, Direct: {row['direct_commits']}",
                        va='center',
                        fontsize=9,
                        color='darkblue'
                    )
                
                # Set author names as y-tick labels with shorter names if needed
                short_names = [name[:25] + '...' if len(name) > 25 else name for name in df['name']]
                plt.yticks(y_pos, short_names)
                
                plt.title(f'Combined Contributor Analysis - {workspace}/{repo_slug}')
                plt.xlabel('Lines of Code')
                plt.ylabel('Contributors')
                plt.legend(loc='lower right')
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.axvline(x=0, color='black', linewidth=0.5)
                
                # Set x-axis limits to make sure there's enough space for labels
                max_add = df['additions'].max()
                max_del = df['deletions'].max()
                plt.xlim(-max_del * 1.2, max_add * 1.4)  # Asymmetric to allow space for PR/commit counts
                
                # Add numbers on the bars for clarity
                for i, v in enumerate(df['additions']):
                    if v > 0 and v > max_add * 0.05:  # Only add text if bar is large enough
                        plt.text(v/2, i, f"{v:,}", 
                                color='white', fontweight='bold', va='center', ha='center')
                
                for i, v in enumerate(df['deletions']):
                    if v > 0 and v > max_del * 0.05:  # Only add text if bar is large enough
                        plt.text(-v/2, i, f"{v:,}", 
                                color='white', fontweight='bold', va='center', ha='center')
                
                # Add total changes as text for each contributor
                for i, row in enumerate(df.itertuples()):
                    plt.text(
                        plt.xlim()[1] * 0.92, 
                        i,
                        f"Total: {row.total_changes:,}",
                        va='center',
                        ha='right',
                        fontsize=9,
                        color='black',
                        fontweight='bold'
                    )
                
                plt.tight_layout()
                plt.savefig(combined_chart_file, dpi=300)
                plt.close()
        
        return render_template('results.html',
                              workspace=workspace,
                              repo_slug=repo_slug,
                              start_date=start_date,
                              end_date=end_date,
                              chart_file=os.path.basename(chart_file),
                              user_chart_file=os.path.basename(user_chart_file),
                              user_stats_file=os.path.basename(user_stats_file),
                              daily_stats_file=os.path.basename(daily_stats_file),
                              direct_commits_file=os.path.basename(direct_commits_file) if direct_commits_file else None,
                              pr_analysis_file=os.path.basename(pr_analysis_file) if pr_analysis_file else None,
                              combined_chart_file=os.path.basename(combined_chart_file) if combined_chart_file else None,
                              user_data=user_data.to_dict('records'))
    
    except Exception as e:
        return render_template('error.html', message=f"Analysis failed: {str(e)}")

@app.route('/download/<filename>')
def download_file(filename):
    """Download a data file"""
    return send_file(f'static/data/{filename}', as_attachment=True)

@app.route('/demo')
def demo():
    """Demo route to show the improved combined chart"""
    # Sample data for the demo
    workspace = "GVT"
    repo_slug = "cx-switch-health-read-assist"
    start_date = "2023-01-01"
    end_date = "2025-06-24"
    
    # Create a unique ID for this analysis session
    analysis_id = f"{workspace}_{repo_slug}_{int(time.time())}"
    
    # Create demo data
    combined_chart_file = f"static/images/{analysis_id}_combined_chart.png"
    
    # Create sample contributor data
    sample_author_stats = {
        'user1': {
            'name': 'Murugan, Sivakumar (HPN)',
            'email': 'sivakumar.murugan@hpe.com',
            'pr_count': 1,
            'direct_commits': 0,
            'additions': 112,
            'deletions': 0,
            'total_changes': 112
        },
        'user2': {
            'name': 'Pandey, Punit Kumar',
            'email': 'punit.pandey@hpe.com',
            'pr_count': 1,
            'direct_commits': 0,
            'additions': 0,
            'deletions': 285,
            'total_changes': 285
        },
        'user3': {
            'name': 'Kallatti, Manjunath',
            'email': 'manjunath.kallatti@hpe.com',
            'pr_count': 1,
            'direct_commits': 0,
            'additions': 0,
            'deletions': 0,
            'total_changes': 0
        },
        'user4': {
            'name': '., Ajay Udayagiri',
            'email': 'ajay.udayagiri@hpe.com',
            'pr_count': 1,
            'direct_commits': 0,
            'additions': 0,
            'deletions': 0,
            'total_changes': 0
        },
        'user5': {
            'name': 'Singh, Harshdeep',
            'email': 'harshdeep.singh@hpe.com',
            'pr_count': 4,
            'direct_commits': 12,
            'additions': 2532,
            'deletions': 124,
            'total_changes': 2656
        },
        'user6': {
            'name': 'Kumar, Amit',
            'email': 'amit.kumar@hpe.com',
            'pr_count': 6,
            'direct_commits': 3,
            'additions': 1421,
            'deletions': 879,
            'total_changes': 2300
        },
        'user7': {
            'name': 'Sharma, Ankit',
            'email': 'ankit.sharma@hpe.com',
            'pr_count': 8,
            'direct_commits': 5,
            'additions': 956,
            'deletions': 654,
            'total_changes': 1610
        }
    }
    
    # Generate combined chart with our sample data
    plt.figure(figsize=(14, 10))  # Larger figure for better readability
    df = pd.DataFrame([
        {
            'name': stats['name'],
            'additions': stats['additions'],
            'deletions': stats['deletions'],
            'total_changes': stats['additions'] + stats['deletions'],
            'pr_count': stats.get('pr_count', 0),
            'direct_commits': stats.get('direct_commits', 0)
        } 
        for stats in sample_author_stats.values()
    ])
    
    # Sort by total activity (additions + deletions) to get most active contributors
    df = df.sort_values('total_changes', ascending=False).head(10)
    
    # The y-position for each author
    y_pos = range(len(df['name']))
    
    # Create horizontal bar chart with more space between bars
    bars_add = plt.barh(y_pos, df['additions'], color='green', alpha=0.7, label='Additions', height=0.4)
    bars_del = plt.barh(y_pos, -df['deletions'], color='red', alpha=0.7, label='Deletions', height=0.4)
    
    # Calculate maximum values for axis scaling and text positioning
    max_add = df['additions'].max() 
    max_del = df['deletions'].max()
    max_val = max(max_add, max_del) * 1.3  # Add 30% margin
    
    # Add PR and direct commit counts
    for i, (_, row) in enumerate(df.iterrows()):
        # Position text on the right side of additions bar with proper offset
        plt.text(
            max_add + (max_val * 0.05),
            i,
            f"PRs: {row['pr_count']}, Direct: {row['direct_commits']}",
            va='center',
            fontsize=9,
            color='darkblue'
        )
        
    # Set author names as y-tick labels with shorter names if needed
    short_names = [name[:25] + '...' if len(name) > 25 else name for name in df['name']]
    plt.yticks(y_pos, short_names)
    
    plt.title(f'Combined Contributor Analysis - {workspace}/{repo_slug}')
    plt.xlabel('Lines of Code')
    plt.ylabel('Contributors')
    plt.legend(loc='lower right')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.axvline(x=0, color='black', linewidth=0.5)
    
    # Set x-axis limits to make sure there's enough space for labels
    plt.xlim(-max_del * 1.2, max_add * 1.4)  # Asymmetric to allow space for PR/commit counts
    
    # Add numbers on the bars for clarity
    for i, v in enumerate(df['additions']):
        if v > 0 and v > max_add * 0.05:  # Only add text if bar is large enough
            plt.text(v/2, i, f"{v:,}", 
                    color='white', fontweight='bold', va='center', ha='center')
    
    for i, v in enumerate(df['deletions']):
        if v > 0 and v > max_del * 0.05:  # Only add text if bar is large enough
            plt.text(-v/2, i, f"{v:,}", 
                    color='white', fontweight='bold', va='center', ha='center')
    
    # Add total changes as text for each contributor
    for i, row in enumerate(df.itertuples()):
        plt.text(
            plt.xlim()[1] * 0.92, 
            i,
            f"Total: {row.total_changes:,}",
            va='center',
            ha='right',
            fontsize=9,
            color='black',
            fontweight='bold'
        )
    
    plt.tight_layout()
    plt.savefig(combined_chart_file, dpi=300)
    plt.close()
    
    # Render template with our demo data
    return render_template('results.html',
                          workspace=workspace,
                          repo_slug=repo_slug,
                          start_date=start_date,
                          end_date=end_date,
                          chart_file='sample_loc_changes.png',
                          user_chart_file='sample_loc_changes.png',
                          user_stats_file='sample_loc_data.csv',
                          daily_stats_file='sample_loc_data.csv',
                          combined_chart_file=os.path.basename(combined_chart_file),
                          user_data=df.to_dict('records'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
