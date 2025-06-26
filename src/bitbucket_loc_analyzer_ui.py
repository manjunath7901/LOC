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
import threading
import queue
from functools import lru_cache
matplotlib.use('Agg')  # Use non-interactive backend for server environments

# Global variables for progress tracking and caching
_analysis_status = {}  # Track analysis progress
_user_cache = {}
_cache_lock = threading.Lock()

def create_simple_chart(data, title, filename, chart_type='bar'):
    """Create simplified, fast-rendering charts optimized for speed"""
    plt.style.use('default')  # Use default style for fastest rendering
    
    # Set up figure with minimal DPI for faster rendering
    fig, ax = plt.subplots(figsize=(10, 5), dpi=75)  # Lower DPI for speed
    
    try:
        print(f"Creating {chart_type} chart: {title}")
        print(f"Data type: {type(data)}, Data shape: {data.shape if hasattr(data, 'shape') else 'No shape'}")
        
        # Check if data is empty or None
        if data is None or (hasattr(data, 'empty') and data.empty) or (hasattr(data, '__len__') and len(data) == 0):
            print("No data available for chart")
            ax.text(0.5, 0.5, 'No data available for chart', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(title)
            plt.savefig(filename, dpi=75, bbox_inches='tight', facecolor='white')
            return
            
        if chart_type == 'time_series':
            print(f"Time series data columns: {data.columns.tolist()}")
            
            if 'date' in data.columns and not data.empty:
                # Limit data points for faster rendering
                display_data = data.tail(50) if len(data) > 50 else data
                
                # Check if we have the required columns
                if 'additions' not in display_data.columns or 'deletions' not in display_data.columns:
                    print("Missing required columns for time series")
                    ax.text(0.5, 0.5, 'Invalid data format for time series chart\nMissing additions or deletions columns', 
                            ha='center', va='center', transform=ax.transAxes, fontsize=12)
                    ax.set_title(title)
                    plt.savefig(filename, dpi=75, bbox_inches='tight', facecolor='white')
                    return
                
                print(f"Creating time series with {len(display_data)} data points")
                print(f"Additions range: {display_data['additions'].min()} to {display_data['additions'].max()}")
                print(f"Deletions range: {display_data['deletions'].min()} to {display_data['deletions'].max()}")
                
                # Simple bar chart without fancy styling
                width = 0.8
                x_positions = range(len(display_data))
                
                ax.bar(x_positions, display_data['additions'], 
                      color='#2E8B57', alpha=0.8, width=width, label='Additions')
                ax.bar(x_positions, -display_data['deletions'], 
                      color='#DC143C', alpha=0.8, width=width, label='Deletions')
                
                # Simple x-axis labels (show every 5th date to avoid clutter)
                if len(display_data) > 10:
                    step = max(1, len(display_data) // 10)
                    tick_positions = range(0, len(display_data), step)
                    tick_labels = [str(display_data.iloc[i]['date']) for i in tick_positions]
                    ax.set_xticks(tick_positions)
                    ax.set_xticklabels(tick_labels, rotation=45, ha='right')
                else:
                    ax.set_xticks(x_positions)
                    ax.set_xticklabels([str(d) for d in display_data['date']], rotation=45, ha='right')
                
                ax.set_ylabel('Lines of Code')
                ax.set_xlabel('Date')
            else:
                print("No valid time series data found")
                ax.text(0.5, 0.5, 'No valid date data available', 
                        ha='center', va='center', transform=ax.transAxes, fontsize=14)
                
        elif chart_type == 'user_contributions':
            print(f"User contributions data columns: {data.columns.tolist()}")
            
            if 'name' in data.columns and not data.empty:
                # Limit to top 10 users for faster rendering
                display_data = data.head(10)
                
                # Check if we have the required columns
                if 'additions' not in display_data.columns or 'deletions' not in display_data.columns:
                    print("Missing required columns for user contributions")
                    ax.text(0.5, 0.5, 'Invalid data format for user contributions chart\nMissing additions or deletions columns', 
                            ha='center', va='center', transform=ax.transAxes, fontsize=12)
                    ax.set_title(title)
                    plt.savefig(filename, dpi=75, bbox_inches='tight', facecolor='white')
                    return
                
                print(f"Creating user contributions chart with {len(display_data)} users")
                for i, row in display_data.iterrows():
                    print(f"User: {row['name']}, Additions: {row['additions']}, Deletions: {row['deletions']}")
                
                # Create horizontal bar chart
                y_pos = range(len(display_data))
                ax.barh(y_pos, display_data['additions'], color='#2E8B57', alpha=0.8, label='Additions')
                ax.barh(y_pos, -display_data['deletions'], color='#DC143C', alpha=0.8, label='Deletions')
                
                # Set user names on y-axis
                ax.set_yticks(y_pos)
                ax.set_yticklabels([str(name) for name in display_data['name']])
                ax.set_xlabel('Lines of Code')
                ax.invert_yaxis()  # Show highest contributor at top
            else:
                print("No valid user contributions data found")
                ax.text(0.5, 0.5, 'No valid user data available', 
                        ha='center', va='center', transform=ax.transAxes, fontsize=14)
                
        # Minimal styling for speed
        ax.set_title(title, fontsize=12, pad=10)
        if ax.get_legend_handles_labels()[0]:  # Only add legend if there are items to show
            ax.legend(loc='best')
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # Tight layout and save with minimal settings
        plt.tight_layout()
        plt.savefig(filename, dpi=75, bbox_inches='tight', facecolor='white', 
                   format='png')
        print(f"Chart saved successfully: {filename}")
        
    except Exception as e:
        print(f"Error creating chart: {e}")
        import traceback
        traceback.print_exc()
        
        # Create a simple error chart
        ax.clear()
        ax.text(0.5, 0.5, f'Chart generation failed:\n{str(e)}', 
                ha='center', va='center', transform=ax.transAxes, fontsize=12)
        ax.set_title(title)
        plt.savefig(filename, dpi=75, bbox_inches='tight', facecolor='white')
        
    finally:
        plt.close(fig)  # Always close to free memory
    
def update_analysis_status(analysis_id, status, progress=0):
    """Update analysis status for progress tracking"""
    global _analysis_status
    _analysis_status[analysis_id] = {
        'status': status,
        'progress': progress,
        'timestamp': time.time()
    }

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

# Global cache for user lookups to speed up repeated analyses
_user_cache = {}
_cache_lock = threading.Lock()

def cache_user_lookup(func):
    """Decorator to cache user lookup results"""
    def wrapper(*args, **kwargs):
        cache_key = str(args) + str(kwargs)
        with _cache_lock:
            if cache_key in _user_cache:
                return _user_cache[cache_key]
            result = func(*args, **kwargs)
            _user_cache[cache_key] = result
            return result
    return wrapper

@app.route('/')
def index():
    """Render the main page with the form"""
    # Get current date and 14 days ago for default values
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    two_weeks_ago = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime('%Y-%m-%d')
    
    return render_template('index.html', 
                          today=today, 
                          two_weeks_ago=two_weeks_ago)

@app.route('/progress/<analysis_id>')
def show_progress(analysis_id):
    """Show progress page for analysis"""
    return render_template('progress.html', analysis_id=analysis_id)

@app.route('/status/<analysis_id>')
def get_analysis_status(analysis_id):
    """Get current analysis status"""
    global _analysis_status
    if analysis_id in _analysis_status:
        return _analysis_status[analysis_id]
    return {'status': 'not_found', 'progress': 0}

@app.route('/results/<analysis_id>')
def show_results(analysis_id):
    """Show analysis results"""
    global _analysis_status
    
    try:
        if analysis_id not in _analysis_status or _analysis_status[analysis_id]['status'] != 'Complete':
            return render_template('error.html', message="Analysis not complete or not found.")
        
        # Find the generated files
        user_stats_file = f"{analysis_id}_user_stats.csv"
        daily_stats_file = f"{analysis_id}_daily_stats.csv"
        chart_file = f"{analysis_id}_chart.png"
        user_chart_file = f"{analysis_id}_user_chart.png"
        
        # Read user data for display
        try:
            user_df = pd.read_csv(f"static/data/{user_stats_file}")
            user_data = user_df.to_dict('records')
        except Exception as e:
            print(f"Warning: Could not read user stats file: {e}")
            user_data = []
        
        # Extract workspace and repo info from analysis_id
        parts = analysis_id.split('_')
        workspace = parts[0] if parts else "Unknown"
        
        # Get the stored analysis parameters - handle both old and new format
        analysis_data = _analysis_status[analysis_id]
        
        if 'params' in analysis_data:
            analysis_params = analysis_data['params']
            start_date = analysis_params.get('start_date', 'N/A')
            end_date = analysis_params.get('end_date', 'N/A')
            repo_slugs = analysis_params.get('repo_slugs', [])
            focus_user = analysis_params.get('focus_user', '')
            analysis_type = analysis_params.get('analysis_type', 'legacy')
        else:
            # Fallback for older analyses - try to extract repo from analysis_id
            start_date = 'N/A'
            end_date = 'N/A'
            repo_slugs = []
            focus_user = ''
            analysis_type = 'legacy'
        
        # If no repo_slugs available, try to extract from analysis_id or use fallback
        if not repo_slugs:
            # Try to parse repo from CSV files or use a reasonable default
            try:
                # Look for user stats file to get repository info
                user_stats_file = f"static/data/{analysis_id}_user_stats.csv"
                if os.path.exists(user_stats_file):
                    user_df = pd.read_csv(user_stats_file)
                    if 'repository' in user_df.columns and len(user_df['repository']) > 0:
                        repo_from_data = user_df['repository'].iloc[0]
                        repo_slugs = [repo_from_data]
            except:
                pass
            
            # Final fallback
            if not repo_slugs:
                repo_slugs = ['Repository Analysis']
        
        # Format repo display
        if isinstance(repo_slugs, list) and len(repo_slugs) == 1:
            repo_display = repo_slugs[0]
        elif isinstance(repo_slugs, list) and len(repo_slugs) > 1:
            repo_display = f"{repo_slugs[0]} (+{len(repo_slugs)-1} more)"
        else:
            repo_display = str(repo_slugs[0]) if repo_slugs else "Repository Analysis"
        
        return render_template('results_new.html',
                              workspace=workspace,
                              repo_slug=repo_display,
                              start_date=start_date,
                              end_date=end_date,
                              focus_user=focus_user,
                              chart_file=chart_file,
                              user_chart_file=user_chart_file,
                              user_stats_file=user_stats_file,
                              daily_stats_file=daily_stats_file,
                              user_data=user_data,
                              analysis_id=analysis_id,
                              analysis_type=analysis_type)
    
    except Exception as e:
        print(f"Error in show_results for {analysis_id}: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', message=f"Error displaying results: {str(e)}")
    
    return render_template('results_new.html',
                          workspace=workspace,
                          repo_slug=repo_display,
                          start_date=start_date,
                          end_date=end_date,
                          focus_user=focus_user,
                          chart_file=chart_file,
                          user_chart_file=user_chart_file,
                          user_stats_file=user_stats_file,
                          daily_stats_file=daily_stats_file,
                          user_data=user_data,
                          analysis_id=analysis_id,
                          analysis_type=analysis_type)

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process the form data and run the analysis"""
    # Get form data
    token = request.form.get('token', '')
    base_url = request.form.get('base_url', 'https://stash.arubanetworks.com')
    workspace = request.form.get('workspace', '')
    repo_slugs_input = request.form.get('repo_slug', '')
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    group_by = request.form.get('group_by', 'day')
    focus_user = request.form.get('focus_user', '').strip()
    analysis_type = request.form.get('analysis_type', 'user_focus')
    include_prs = 'include_prs' in request.form
    include_direct = 'include_direct' in request.form
    
    # Validate analysis type and focus user
    if analysis_type == 'user_focus' and not focus_user:
        return render_template('error.html', message="User-focused analysis requires a user email to be specified.")
    
    # For overall analysis, clear focus_user to ensure we get all users
    if analysis_type == 'overall':
        focus_user = ''
    
    # Split repository slugs (comma-separated)
    repo_slugs = [slug.strip() for slug in repo_slugs_input.split(',') if slug.strip()]
    
    if not repo_slugs:
        return render_template('error.html', message="No repository slugs provided. Please enter at least one repository.")
    
    # Generate unique analysis ID based on analysis type
    if analysis_type == 'overall':
        analysis_id = f"{workspace}_overall_{int(time.time())}_{hash(token) % 10000}"
    else:
        analysis_id = f"{workspace}_user_{int(time.time())}_{hash(token) % 10000}"
    
    # Store analysis parameters for later use
    _analysis_status[analysis_id] = {
        'status': 'pending',
        'progress': 0,
        'params': {
            'workspace': workspace,
            'repo_slugs': repo_slugs,
            'start_date': start_date,
            'end_date': end_date,
            'focus_user': focus_user,
            'group_by': group_by,
            'analysis_type': analysis_type
        }
    }
    
    # Start background analysis
    def run_analysis():
        try:
            update_analysis_status(analysis_id, "Initializing...", 10)
            
            # File paths for output
            user_stats_file = f"static/data/{analysis_id}_user_stats.csv"
            daily_stats_file = f"static/data/{analysis_id}_daily_stats.csv"
            chart_file = f"static/images/{analysis_id}_chart.png"
            user_chart_file = f"static/images/{analysis_id}_user_chart.png"
            
            update_analysis_status(analysis_id, "Connecting to Bitbucket...", 20)
            analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
            
            # Use different analysis functions based on type
            if analysis_type == 'overall':
                update_analysis_status(analysis_id, "Analyzing all repository contributors...", 40)
                daily_data, user_data, repo_summary = analyze_multiple_repositories_overall(
                    analyzer, workspace, repo_slugs, start_date, end_date, group_by
                )
            else:
                update_analysis_status(analysis_id, "Analyzing user-focused repositories...", 40)
                daily_data, user_data, repo_summary = analyze_multiple_repositories(
                    analyzer, workspace, repo_slugs, start_date, end_date, group_by, focus_user
                )
            
            if daily_data is None or user_data is None:
                update_analysis_status(analysis_id, "Error: No data found", 0)
                return
            
            # Check if dataframes are empty
            if daily_data is None or user_data is None or daily_data.empty or user_data.empty:
                if focus_user:
                    update_analysis_status(analysis_id, f"Error: No data found for user '{focus_user}'", 0)
                else:
                    update_analysis_status(analysis_id, "Error: No data found in the specified time range", 0)
                return
            
            # Apply smart user matching if focus_user is specified
            if focus_user:
                print(f"Applying smart user matching for user: '{focus_user}'")
                original_user_count = len(user_data)
                
                # Use the same smart matching logic as elsewhere in the system
                matching_users = []
                for idx, row in user_data.iterrows():
                    if analyzer.is_user_match(focus_user, row['name']):
                        matching_users.append(idx)
                
                if matching_users:
                    user_data = user_data.loc[matching_users]
                    print(f"Smart user matching: {original_user_count} -> {len(user_data)} users")
                else:
                    print(f"Smart user matching: {original_user_count} -> 0 users")
                    update_analysis_status(analysis_id, f"Error: No users matching '{focus_user}' found", 0)
                    return
                
                # Also filter daily data to match the filtered users
                if 'author' in daily_data.columns:
                    valid_authors = user_data['name'].tolist()
                    daily_data = daily_data[daily_data['author'].isin(valid_authors)]
                    print(f"Filtered daily data to {len(daily_data)} records")
            
            update_analysis_status(analysis_id, "Saving data files...", 60)
            daily_data.to_csv(daily_stats_file, index=False)
            user_data.to_csv(user_stats_file, index=False)
            
            update_analysis_status(analysis_id, "Generating time series chart...", 75)
            
            # Create simplified time series chart
            daily_summary = daily_data.groupby('date').agg({
                'additions': 'sum', 'deletions': 'sum'
            }).reset_index()
            
            # Debug: Print what we have for daily_summary
            print(f"Daily summary data shape: {daily_summary.shape}")
            print(f"Daily summary columns: {daily_summary.columns.tolist()}")
            if not daily_summary.empty:
                print(f"Daily summary sample: {daily_summary.head()}")
            
            repo_title = f"{len(repo_slugs)} repositories" if len(repo_slugs) > 1 else repo_slugs[0]
            title_prefix = f"Changes for {focus_user} in" if focus_user else "Changes in"
            
            create_simple_chart(
                daily_summary, 
                f'{title_prefix} {workspace}/{repo_title}', 
                chart_file, 
                'time_series'
            )
            
            update_analysis_status(analysis_id, "Generating contributor chart...", 85)
            
            # Create simplified user chart (top contributors only)
            if focus_user:
                # When focusing on a user, show their individual data
                top_users = user_data.groupby('name').agg({
                    'additions': 'sum', 'deletions': 'sum'
                }).reset_index().head(5)
            else:
                user_summary = user_data.groupby('name').agg({
                    'additions': 'sum', 'deletions': 'sum'
                }).reset_index()
                top_users = user_summary.sort_values('additions', ascending=False).head(10)
            
            # Debug: Print what we have for top_users
            print(f"Top users data shape: {top_users.shape}")
            print(f"Top users columns: {top_users.columns.tolist()}")
            if not top_users.empty:
                print(f"Top users sample: {top_users.head()}")
            
            create_simple_chart(
                top_users, 
                f'Top Contributors - {workspace}', 
                user_chart_file, 
                'user_contributions'
            )
            
            update_analysis_status(analysis_id, "Finalizing results...", 95)
            
            update_analysis_status(analysis_id, "Complete", 100)
            
        except Exception as e:
            print(f"Analysis error: {e}")
            update_analysis_status(analysis_id, f"Error: {str(e)}", 0)
    
    # Start analysis in background thread
    thread = threading.Thread(target=run_analysis)
    thread.daemon = True
    thread.start()
    
    # Redirect to progress page
    return redirect(url_for('show_progress', analysis_id=analysis_id))

@app.route('/download/<filename>')
def download_file(filename):
    """Download CSV data files"""
    try:
        file_path = os.path.join('static/data', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return render_template('error.html', message=f"File {filename} not found.")
    except Exception as e:
        return render_template('error.html', message=f"Error downloading file: {str(e)}")

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

def analyze_multiple_repositories(analyzer, workspace, repo_slugs, start_date, end_date, group_by, focus_user=None):
    """Analyze multiple repositories and combine the results with strict user filtering.
    
    Args:
        analyzer: BitbucketLOCAnalyzer instance
        workspace: Workspace/project key
        repo_slugs: List of repository slugs
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        group_by: How to group results (day, week, month)
        focus_user: Optional username to focus on (will apply strict filtering)
        
    Returns:
        tuple: (combined_daily_data, combined_user_data, repo_summary)
    """
    all_daily_data = []
    all_user_data = []
    repo_summary = []
    
    print(f"Starting analysis for {len(repo_slugs)} repositories...")
    if focus_user:
        print(f"Applying strict filtering for user: '{focus_user}'")
    
    for i, repo_slug in enumerate(repo_slugs):
        print(f"Analyzing repository {i+1}/{len(repo_slugs)}: {workspace}/{repo_slug}...")
        
        # Pass focus_user to the analyzer so filtering happens early
        results = analyzer.analyze_repository(
            workspace,
            repo_slug,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            by_user=True,
            focus_user=focus_user  # This will filter at the commit level
        )
        
        if not results or len(results) < 2:
            print(f"Warning: Skipping repository {repo_slug} due to incomplete results")
            continue
            
        daily_data, user_data = results
        
        # Additional strict filtering if focus_user is specified
        if focus_user and not user_data.empty:
            original_count = len(user_data)
            
            # Use the same smart matching logic as the commit-level filtering
            if len(focus_user) >= 3:
                try:
                    # Apply the same is_user_match logic that works at commit level
                    matching_users = []
                    for idx, row in user_data.iterrows():
                        if analyzer.is_user_match(focus_user, row['name']):
                            matching_users.append(idx)
                    
                    if matching_users:
                        user_data = user_data.loc[matching_users]
                    else:
                        # If no matches found with smart matching, empty the dataset
                        user_data = user_data.iloc[0:0]  # Empty DataFrame with same structure
                        
                except Exception as e:
                    print(f"Error filtering user data: {e}")
                    # If filtering fails, keep original data
                    pass
            
            print(f"Repository {repo_slug}: Filtered from {original_count} to {len(user_data)} users")
            
            if user_data.empty:
                print(f"No matching users found in {repo_slug}, skipping...")
                continue
        
        # Add repository information to the data
        daily_data['repository'] = repo_slug
        user_data['repository'] = repo_slug
        
        all_daily_data.append(daily_data)
        all_user_data.append(user_data)
        
        # Add summary for this repository
        total_additions = daily_data['additions'].sum()
        total_deletions = daily_data['deletions'].sum()
        repo_summary.append({
            'repository': repo_slug,
            'additions': total_additions,
            'deletions': total_deletions,
            'total_changes': total_additions + total_deletions,
            'commits': len(daily_data),
            'contributors': len(user_data)
        })
        
        print(f"Repository {repo_slug}: {len(daily_data)} commits, {len(user_data)} contributors")
    
    if not all_daily_data:
        print("No data collected from any repository")
        return None, None, None
        
    # Combine all data
    combined_daily_data = pd.concat(all_daily_data, ignore_index=True)
    combined_user_data = pd.concat(all_user_data, ignore_index=True)
    
    print(f"Final combined data: {len(combined_daily_data)} daily records, {len(combined_user_data)} user records")
    
    # Create a repository summary dataframe
    repo_summary_df = pd.DataFrame(repo_summary)
    
    return combined_daily_data, combined_user_data, repo_summary_df

def analyze_multiple_repositories_overall(analyzer, workspace, repo_slugs, start_date, end_date, group_by):
    """Analyze multiple repositories for overall stats (no user filtering).
    
    Args:
        analyzer: BitbucketLOCAnalyzer instance
        workspace: Workspace/project key
        repo_slugs: List of repository slugs
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        group_by: How to group results (day, week, month)
        
    Returns:
        tuple: (combined_daily_data, combined_user_data, repo_summary)
    """
    all_daily_data = []
    all_user_data = []
    repo_summary = []
    
    print(f"Starting overall analysis for {len(repo_slugs)} repositories (no user filtering)...")
    
    for i, repo_slug in enumerate(repo_slugs):
        print(f"Analyzing repository {i+1}/{len(repo_slugs)}: {workspace}/{repo_slug} (all users)...")
        
        # Get all users - no focus_user filtering
        results = analyzer.analyze_repository(
            workspace,
            repo_slug,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            by_user=True,
            focus_user=None  # No user filtering for overall stats
        )
        
        if not results or len(results) < 2:
            print(f"Warning: Skipping repository {repo_slug} due to incomplete results")
            continue
            
        daily_data, user_data = results
        
        if not daily_data.empty and not user_data.empty:
            # Add repository information
            daily_data['repository'] = repo_slug
            user_data['repository'] = repo_slug
            
            all_daily_data.append(daily_data)
            all_user_data.append(user_data)
            
            # Store summary
            repo_summary.append({
                'repository': repo_slug,
                'total_commits': len(daily_data),
                'total_additions': daily_data['additions'].sum(),
                'total_deletions': daily_data['deletions'].sum(),
                'users_found': len(user_data)
            })
            
            print(f"Repository {repo_slug}: {len(daily_data)} commits, {len(user_data)} contributors")
    
    if not all_daily_data:
        print("No data collected from any repository")
        return None, None, []
    
    # Combine all data
    combined_daily_data = pd.concat(all_daily_data, ignore_index=True)
    combined_user_data = pd.concat(all_user_data, ignore_index=True)
    
    # Group user data by name and email (same user might appear in multiple repositories)
    user_aggregated = combined_user_data.groupby(['name', 'email']).agg({
        'commits': 'sum',
        'additions': 'sum', 
        'deletions': 'sum'
    }).reset_index()
    
    # Calculate total changes
    user_aggregated['total_changes'] = user_aggregated['additions'] + user_aggregated['deletions']
    user_aggregated = user_aggregated.sort_values('total_changes', ascending=False)
    
    print(f"Overall analysis complete: {len(combined_daily_data)} daily records, {len(user_aggregated)} unique users")
    print(f"Final combined data: {len(combined_daily_data)} daily records, {len(user_aggregated)} user records")
    
    return combined_daily_data, user_aggregated, repo_summary

@app.route('/analyze_user_only', methods=['POST'])
def analyze_user_only():
    """Process user-only analysis (much faster for focused user analysis)"""
    # Get form data
    token = request.form.get('token', '')
    base_url = request.form.get('base_url', 'https://stash.arubanetworks.com')
    workspace = request.form.get('workspace', '')
    repo_slugs_input = request.form.get('repo_slug', '')
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    group_by = request.form.get('group_by', 'day')
    focus_user = request.form.get('focus_user', '').strip()
    
    if not focus_user:
        return render_template('error.html', message="User-only analysis requires a focus user to be specified.")
    
    # Split repository slugs (comma-separated)
    repo_slugs = [slug.strip() for slug in repo_slugs_input.split(',') if slug.strip()]
    
    if not repo_slugs:
        return render_template('error.html', message="No repository slugs provided. Please enter at least one repository.")
    
    # Generate unique analysis ID
    analysis_id = f"{workspace}_user_{int(time.time())}_{hash(token) % 10000}"
    
    # Store analysis parameters
    _analysis_status[analysis_id] = {
        'status': 'pending',
        'progress': 0,
        'type': 'user_only',
        'params': {
            'workspace': workspace,
            'repo_slugs': repo_slugs,
            'start_date': start_date,
            'end_date': end_date,
            'focus_user': focus_user,
            'group_by': group_by,
            'token': token,
            'base_url': base_url
        }
    }
    
    # Start background user-only analysis
    def run_user_analysis():
        try:
            update_analysis_status(analysis_id, "Initializing user analysis...", 10)
            
            # File paths for output
            user_stats_file = f"static/data/{analysis_id}_user_stats.csv"
            daily_stats_file = f"static/data/{analysis_id}_daily_stats.csv"
            chart_file = f"static/images/{analysis_id}_chart.png"
            user_chart_file = f"static/images/{analysis_id}_user_chart.png"
            
            update_analysis_status(analysis_id, "Connecting to Bitbucket...", 20)
            analyzer = BitbucketLOCAnalyzer(base_url=base_url, token=token)
            
            update_analysis_status(analysis_id, "Analyzing user contributions...", 40)
            
            # User-focused analysis - only get commits from the specific user
            daily_data, user_data, repo_summary = analyze_user_focused_repositories(
                analyzer, workspace, repo_slugs, start_date, end_date, group_by, focus_user
            )
            
            if daily_data is None or user_data is None or user_data.empty:
                update_analysis_status(analysis_id, f"Error: No data found for user '{focus_user}'", 0)
                return
            
            update_analysis_status(analysis_id, "Saving data files...", 60)
            daily_data.to_csv(daily_stats_file, index=False)
            user_data.to_csv(user_stats_file, index=False)
            
            update_analysis_status(analysis_id, "Generating charts...", 75)
            
            # Create charts
            daily_summary = daily_data.groupby('date').agg({
                'additions': 'sum', 'deletions': 'sum'
            }).reset_index()
            
            repo_title = f"{len(repo_slugs)} repositories" if len(repo_slugs) > 1 else repo_slugs[0]
            
            create_simple_chart(
                daily_summary, 
                f'Changes for {focus_user} in {workspace}/{repo_title}', 
                chart_file, 
                'time_series'
            )
            
            create_simple_chart(
                user_data, 
                f'Top Contributors - {workspace}', 
                user_chart_file, 
                'user_contributions'
            )
            
            update_analysis_status(analysis_id, "Complete", 100)
            
        except Exception as e:
            print(f"Error in user analysis: {e}")
            import traceback
            traceback.print_exc()
            update_analysis_status(analysis_id, f"Error: {str(e)}", 0)
    
    # Start the analysis in a background thread
    thread = threading.Thread(target=run_user_analysis)
    thread.daemon = True
    thread.start()
    
    return redirect(url_for('show_progress', analysis_id=analysis_id))

@app.route('/analyze_overall/<analysis_id>')
def analyze_overall(analysis_id):
    """Analyze overall repository stats for an existing user analysis"""
    if analysis_id not in _analysis_status:
        return render_template('error.html', message="Analysis not found.")
    
    # Get the original parameters - handle both old and new format
    analysis_data = _analysis_status[analysis_id]
    
    if 'params' in analysis_data:
        params = analysis_data['params']
    else:
        # For older analyses without stored params, show message with option to reload
        print(f"Analysis {analysis_id} missing params. Available keys: {list(analysis_data.keys())}")
        
        # Try to extract basic info from the analysis_id
        parts = analysis_id.split('_')
        if len(parts) >= 2:
            workspace = parts[0]
            # Show a user-friendly message with the option to re-run analysis
            return render_template('error.html', 
                                 message=f"""
                                 <div class="alert alert-warning">
                                     <h5>Overall Repository Stats Not Available</h5>
                                     <p>This analysis ({workspace}) was created with an older version that doesn't support lazy-loading of overall stats.</p>
                                     <p><strong>To access overall repository statistics:</strong></p>
                                     <ol>
                                         <li>Click "Start New Analysis" below</li>
                                         <li>Fill in your repository details</li>
                                         <li>Leave the "Focus User" field <strong>empty</strong> for overall stats</li>
                                         <li>Submit the analysis</li>
                                     </ol>
                                     <p>This will give you access to all repository statistics including the overall stats tab.</p>
                                     <div class="mt-3">
                                         <a href="/" class="btn btn-primary">Start New Analysis</a>
                                     </div>
                                 </div>
                                 """)
        else:
            return render_template('error.html', 
                                 message="This analysis doesn't support overall stats loading. Please start a new analysis to use this feature.")
    
    # Create new analysis ID for overall stats
    overall_analysis_id = f"{analysis_id}_overall"
    
    # Check if overall analysis already exists and is complete
    if overall_analysis_id in _analysis_status and _analysis_status[overall_analysis_id]['status'] == 'Complete':
        return redirect(url_for('show_results', analysis_id=overall_analysis_id))
    
    # Store analysis parameters for overall analysis
    _analysis_status[overall_analysis_id] = {
        'status': 'pending',
        'progress': 0,
        'type': 'overall',
        'params': params
    }
    
    def run_overall_analysis():
        try:
            update_analysis_status(overall_analysis_id, "Initializing overall analysis...", 10)
            
            # File paths for output
            user_stats_file = f"static/data/{overall_analysis_id}_user_stats.csv"
            daily_stats_file = f"static/data/{overall_analysis_id}_daily_stats.csv"
            chart_file = f"static/images/{overall_analysis_id}_chart.png"
            user_chart_file = f"static/images/{overall_analysis_id}_user_chart.png"
            
            update_analysis_status(overall_analysis_id, "Connecting to Bitbucket...", 20)
            analyzer = BitbucketLOCAnalyzer(base_url=params['base_url'], token=params['token'])
            
            update_analysis_status(overall_analysis_id, "Analyzing all repositories (no user filter)...", 40)
            
            # Full repository analysis (no user filter)
            daily_data, user_data, repo_summary = analyze_multiple_repositories_overall(
                analyzer, params['workspace'], params['repo_slugs'], 
                params['start_date'], params['end_date'], params['group_by']
            )
            
            if daily_data is None or user_data is None or daily_data.empty or user_data.empty:
                update_analysis_status(overall_analysis_id, "Error: No data found for overall analysis", 0)
                return
            
            update_analysis_status(overall_analysis_id, "Saving overall data files...", 60)
            daily_data.to_csv(daily_stats_file, index=False)
            user_data.to_csv(user_stats_file, index=False)
            
            update_analysis_status(overall_analysis_id, "Generating overall charts...", 75)
            
            # Create charts
            daily_summary = daily_data.groupby('date').agg({
                'additions': 'sum', 'deletions': 'sum'
            }).reset_index()
            
            repo_title = f"{len(params['repo_slugs'])} repositories" if len(params['repo_slugs']) > 1 else params['repo_slugs'][0]
            
            create_simple_chart(
                daily_summary, 
                f'Overall Changes in {params["workspace"]}/{repo_title}', 
                chart_file, 
                'time_series'
            )
            
            create_simple_chart(
                user_data, 
                f'All Contributors - {params["workspace"]}', 
                user_chart_file, 
                'user_contributions'
            )
            
            update_analysis_status(overall_analysis_id, "Complete", 100)
            
        except Exception as e:
            print(f"Error in overall analysis: {e}")
            import traceback
            traceback.print_exc()
            update_analysis_status(overall_analysis_id, f"Error: {str(e)}", 0)
    
    # Start the analysis in a background thread
    thread = threading.Thread(target=run_overall_analysis)
    thread.daemon = True
    thread.start()
    
    return redirect(url_for('show_progress', analysis_id=overall_analysis_id))

def analyze_user_focused_repositories(analyzer, workspace, repo_slugs, start_date, end_date, group_by, focus_user):
    """Analyze repositories with focus on a specific user - much faster than full analysis.
    
    Args:
        analyzer: BitbucketLOCAnalyzer instance
        workspace: Workspace/project key
        repo_slugs: List of repository slugs
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        group_by: How to group results (day, week, month)
        focus_user: Username to focus on
        
    Returns:
        tuple: (daily_data, user_data, repo_summary)
    """
    all_daily_data = []
    all_user_data = []
    repo_summary = []
    
    print(f"Starting user-focused analysis for '{focus_user}' across {len(repo_slugs)} repositories...")
    
    for i, repo_slug in enumerate(repo_slugs):
        print(f"Analyzing repository {i+1}/{len(repo_slugs)}: {workspace}/{repo_slug} for user '{focus_user}'...")
        
        # Get only commits from the specific user - this is much faster
        results = analyzer.analyze_repository(
            workspace,
            repo_slug,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
            by_user=True,
            focus_user=focus_user  # This filters at the commit level, making it much faster
        )
        
        if not results or len(results) < 2:
            print(f"No data found for user '{focus_user}' in repository {repo_slug}")
            continue
            
        daily_data, user_data = results
        
        if not daily_data.empty and not user_data.empty:
            # Add repository information
            daily_data['repository'] = repo_slug
            user_data['repository'] = repo_slug
            
            all_daily_data.append(daily_data)
            all_user_data.append(user_data)
            
            # Store summary
            repo_summary.append({
                'repository': repo_slug,
                'total_commits': len(daily_data),
                'total_additions': daily_data['additions'].sum(),
                'total_deletions': daily_data['deletions'].sum(),
                'users_found': len(user_data)
            })
    
    if not all_daily_data:
        print(f"No data found for user '{focus_user}' in any repository")
        return None, None, []
    
    # Combine all data
    combined_daily_data = pd.concat(all_daily_data, ignore_index=True)
    combined_user_data = pd.concat(all_user_data, ignore_index=True)
    
    # Group user data by name (same user might appear in multiple repositories)
    user_aggregated = combined_user_data.groupby(['name', 'email']).agg({
        'commits': 'sum',
        'additions': 'sum', 
        'deletions': 'sum'
    }).reset_index()
    
    # Calculate total changes
    user_aggregated['total_changes'] = user_aggregated['additions'] + user_aggregated['deletions']
    user_aggregated = user_aggregated.sort_values('total_changes', ascending=False)
    
    print(f"User-focused analysis complete: {len(combined_daily_data)} daily records, {len(user_aggregated)} unique users")
    
    return combined_daily_data, user_aggregated, repo_summary

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
