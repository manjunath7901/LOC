#!/usr/bin/env python3
"""
Simple Bitbucket LOC Analyzer Web Interface

This restores the original, simple approach where users can:
- Choose between user-focused analysis or overall repository stats
- Analyze one or multiple repositories
- Get separate, clear charts for each repository
- See combined stats for multiple repositories
- Simple form submission with immediate results
"""

from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import os
import tempfile
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import threading
import uuid
import time
from functools import lru_cache

# Use non-interactive backend
matplotlib.use('Agg')

# Import the original analyzer
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

app = Flask(__name__)

# Global variables for caching and progress tracking
_user_cache = {}
_cache_lock = threading.Lock()
_analysis_progress = {}
_progress_lock = threading.Lock()

def get_cached_user_data(cache_key, analyzer_func):
    """Get cached user data or compute if not cached"""
    with _cache_lock:
        if cache_key in _user_cache:
            print(f"Cache hit for {cache_key}")
            return _user_cache[cache_key]
        
        print(f"Cache miss for {cache_key}, computing...")
        result = analyzer_func()
        _user_cache[cache_key] = result
        return result

def update_progress(analysis_id, status, progress):
    """Update analysis progress"""
    with _progress_lock:
        _analysis_progress[analysis_id] = {
            'status': status,
            'progress': progress,
            'timestamp': time.time()
        }

def get_progress(analysis_id):
    """Get current progress for analysis"""
    with _progress_lock:
        return _analysis_progress.get(analysis_id, {'status': 'Starting...', 'progress': 0})

def parse_repositories(repo_input):
    """Parse repository input - can be comma-separated or line-separated"""
    if not repo_input:
        return []
    
    repos = []
    for line in repo_input.split('\n'):
        for repo in line.split(','):
            repo = repo.strip()
            if repo:
                repos.append(repo)
    
    return repos

def create_chart(data, title, filename):
    """Create a chart from the data"""
    plt.figure(figsize=(12, 6))
    
    if data is None or data.empty:
        plt.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                transform=plt.gca().transAxes, fontsize=16)
        plt.title(title)
        plt.savefig(filename, bbox_inches='tight', dpi=100)
        plt.close()
        return
    
    # Create time series chart
    if 'date' in data.columns:
        x = range(len(data))
        plt.bar(x, data['additions'], color='green', alpha=0.7, label='Additions')
        plt.bar(x, -data['deletions'], color='red', alpha=0.7, label='Deletions')
        
        # Set x-axis labels
        if len(data) > 20:
            step = len(data) // 10
            plt.xticks(range(0, len(data), step), 
                      [str(data.iloc[i]['date']) for i in range(0, len(data), step)], 
                      rotation=45)
        else:
            plt.xticks(x, [str(d) for d in data['date']], rotation=45)
        
        plt.xlabel('Date')
        plt.ylabel('Lines of Code')
        plt.legend()
        plt.grid(True, alpha=0.3)
    
    plt.title(title)
    plt.tight_layout()
    plt.savefig(filename, bbox_inches='tight', dpi=100)
    plt.close()

@app.route('/')
def index():
    """Main page with the analysis form"""
    return render_template('simple_form.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Handle form submission and start background analysis"""
    try:
        # Get form data
        token = request.form.get('token')
        base_url = request.form.get('base_url', 'https://stash.arubanetworks.com')
        workspace = request.form.get('workspace')
        repo_input = request.form.get('repositories', '')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        group_by = request.form.get('group_by', 'day')
        analysis_type = request.form.get('analysis_type', 'overall')
        focus_user = request.form.get('focus_user', '').strip()
        
        # Validate required fields
        if not all([token, base_url, workspace, repo_input, start_date, end_date]):
            return render_template('simple_form.html', 
                                 error="Please fill in all required fields")
        
        # Validate analysis type specific requirements
        if analysis_type == 'user_focus' and not focus_user:
            return render_template('simple_form.html', 
                                 error="User-focused analysis requires a user email to be specified")
        
        # Parse repositories
        repositories = parse_repositories(repo_input)
        if not repositories:
            return render_template('simple_form.html', 
                                 error="Please enter at least one repository")
        
        # Generate unique analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Store analysis parameters
        analysis_params = {
            'token': token,
            'base_url': base_url,
            'workspace': workspace,
            'repositories': repositories,
            'start_date': start_date,
            'end_date': end_date,
            'group_by': group_by,
            'analysis_type': analysis_type,
            'focus_user': focus_user
        }
        
        # Initialize progress
        update_progress(analysis_id, "Initializing analysis...", 0)
        
        # Start background analysis
        thread = threading.Thread(target=run_background_analysis, args=(analysis_id, analysis_params))
        thread.daemon = True
        thread.start()
        
        # Redirect to progress page
        return redirect(url_for('progress', analysis_id=analysis_id))
        
    except Exception as e:
        print(f"Error in analysis setup: {str(e)}")
        return render_template('simple_form.html', 
                             error=f"Analysis setup failed: {str(e)}")

def run_background_analysis(analysis_id, params):
    """Run analysis in background thread"""
    try:
        repositories = params['repositories']
        token = params['token']
        base_url = params['base_url']
        workspace = params['workspace']
        start_date = params['start_date']
        end_date = params['end_date']
        group_by = params['group_by']
        analysis_type = params['analysis_type']
        focus_user = params['focus_user']
        
        update_progress(analysis_id, "Setting up analysis environment...", 5)
        
        # Prepare results data
        results = {
            'workspace': workspace,
            'repositories': repositories,
            'start_date': start_date,
            'end_date': end_date,
            'group_by': group_by,
            'analysis_type': analysis_type,
            'focus_user': focus_user,
            'repo_results': [],
            'charts': [],
            'overall_stats': None,
            'analysis_id': analysis_id
        }
        
        # Create temporary directory for charts
        temp_dir = tempfile.mkdtemp()
        
        # Analyze each repository
        all_data = []
        all_user_data = []
        
        total_repos = len(repositories)
        for i, repo_slug in enumerate(repositories):
            progress_base = 10 + (i * 70 // total_repos)
            update_progress(analysis_id, f"Analyzing repository {i+1}/{total_repos}: {repo_slug}...", progress_base)
            
            try:
                # Create cache key for this analysis
                cache_key = f"{workspace}_{repo_slug}_{start_date}_{end_date}_{group_by}_{analysis_type}_{focus_user}"
                
                # Create analyzer with correct parameters
                analyzer = BitbucketLOCAnalyzer(
                    base_url=base_url,
                    token=token
                )
                
                update_progress(analysis_id, f"Fetching data for {repo_slug}...", progress_base + 10)
                
                # Define analyzer function for caching
                def get_analysis_data():
                    if analysis_type == 'user_focus':
                        # User-focused analysis - single user only
                        data = analyzer.analyze_repository(
                            workspace=workspace,
                            repo_slug=repo_slug,
                            start_date=start_date,
                            end_date=end_date,
                            group_by=group_by,
                            focus_user=focus_user
                        )
                        return data, None  # Return tuple for consistency
                    else:
                        # Overall repository analysis - get all users
                        result = analyzer.analyze_repository(
                            workspace=workspace,
                            repo_slug=repo_slug,
                            start_date=start_date,
                            end_date=end_date,
                            group_by=group_by,
                            by_user=True  # Get user statistics for overall analysis
                        )
                        # analyze_repository returns tuple (data, user_data) when by_user=True
                        return result
                
                # Get data with caching
                result = get_cached_user_data(cache_key, get_analysis_data)
                
                update_progress(analysis_id, f"Processing data for {repo_slug}...", progress_base + 15)
                
                # Handle the result based on analysis type
                if analysis_type == 'user_focus':
                    data, user_data = result
                else:
                    # For overall analysis, we get (data, user_data) tuple
                    if isinstance(result, tuple) and len(result) == 2:
                        data, user_data = result
                    else:
                        data = result
                        user_data = None
                
                if data is not None and not data.empty:
                    all_data.append(data)
                    if user_data is not None and not user_data.empty:
                        all_user_data.append(user_data)
                    
                    # Calculate stats for this repo
                    total_additions = data['additions'].sum()
                    total_deletions = data['deletions'].sum()
                    total_commits = len(data)
                    
                    update_progress(analysis_id, f"Creating chart for {repo_slug}...", progress_base + 20)
                    
                    # Create chart for this repository
                    chart_filename = f"chart_{i}.png"
                    chart_path = os.path.join(temp_dir, chart_filename)
                    
                    if analysis_type == 'user_focus':
                        chart_title = f"{repo_slug} - {focus_user} Contributions"
                    else:
                        chart_title = f"{repo_slug} - Overall Activity"
                    
                    create_chart(data, chart_title, chart_path)
                    
                    # Store result
                    repo_result = {
                        'repo_slug': repo_slug,
                        'total_additions': total_additions,
                        'total_deletions': total_deletions,
                        'net_change': total_additions - total_deletions,
                        'total_commits': total_commits,
                        'chart_file': chart_filename,
                        'success': True,
                        'analysis_type': analysis_type,
                        'user_data': user_data.to_dict('records') if user_data is not None and not user_data.empty else None
                    }
                else:
                    repo_result = {
                        'repo_slug': repo_slug,
                        'success': False,
                        'error': f'No data found for {"user " + focus_user if analysis_type == "user_focus" else "repository"} in the specified date range'
                    }
                
                results['repo_results'].append(repo_result)
                
            except Exception as e:
                print(f"Error analyzing {repo_slug}: {str(e)}")
                repo_result = {
                    'repo_slug': repo_slug,
                    'success': False,
                    'error': str(e)
                }
                results['repo_results'].append(repo_result)
        
        update_progress(analysis_id, "Generating overall statistics...", 85)
        
        # Calculate overall stats if we have multiple repositories
        if len(repositories) > 1 and all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            if 'date' in combined_data.columns:
                # Group by date to avoid duplicates
                combined_data = combined_data.groupby('date').agg({
                    'additions': 'sum',
                    'deletions': 'sum'
                }).reset_index()
            
            overall_additions = combined_data['additions'].sum()
            overall_deletions = combined_data['deletions'].sum()
            overall_commits = len(combined_data)
            
            results['overall_stats'] = {
                'total_additions': overall_additions,
                'total_deletions': overall_deletions,
                'net_change': overall_additions - overall_deletions,
                'total_commits': overall_commits,
                'num_repos': len([r for r in results['repo_results'] if r['success']]),
                'analysis_type': analysis_type
            }
            
            # Create combined chart
            overall_chart_path = os.path.join(temp_dir, "overall_chart.png")
            if analysis_type == 'user_focus':
                overall_title = f"Combined Activity - {focus_user} Across Repositories"
            else:
                overall_title = "Combined Repository Activity - All Contributors"
            
            create_chart(combined_data, overall_title, overall_chart_path)
            results['overall_chart'] = "overall_chart.png"
        
        # Store temp directory for serving files
        results['temp_dir'] = temp_dir
        
        update_progress(analysis_id, "Analysis completed successfully!", 100)
        
        # Store results for retrieval
        with _progress_lock:
            _analysis_progress[analysis_id]['results'] = results
            _analysis_progress[analysis_id]['completed'] = True
        
    except Exception as e:
        print(f"Error in background analysis: {str(e)}")
        update_progress(analysis_id, f"Analysis failed: {str(e)}", -1)

@app.route('/progress/<analysis_id>')
def progress(analysis_id):
    """Show progress page for ongoing analysis"""
    return render_template('progress.html', analysis_id=analysis_id)

@app.route('/status/<analysis_id>')
def get_status(analysis_id):
    """Get analysis status and progress via AJAX"""
    with _progress_lock:
        if analysis_id not in _analysis_progress:
            return jsonify({'status': 'not_found', 'progress': 0})
        
        progress_data = _analysis_progress[analysis_id]
        
        if progress_data.get('completed'):
            return jsonify({
                'status': 'Complete',
                'progress': 100,
                'completed': True
            })
        elif progress_data.get('progress', 0) < 0:
            return jsonify({
                'status': progress_data.get('status', 'Error occurred'),
                'progress': 0,
                'error': True
            })
        else:
            return jsonify({
                'status': progress_data.get('status', 'Processing...'),
                'progress': progress_data.get('progress', 0)
            })

@app.route('/results/<analysis_id>')
def show_results(analysis_id):
    """Show analysis results"""
    with _progress_lock:
        if analysis_id not in _analysis_progress:
            return render_template('simple_form.html', 
                                 error="Analysis not found. Please start a new analysis.")
        
        progress_data = _analysis_progress[analysis_id]
        
        if not progress_data.get('completed'):
            return redirect(url_for('progress', analysis_id=analysis_id))
        
        if 'results' not in progress_data:
            return render_template('simple_form.html', 
                                 error="Analysis results not available. Please start a new analysis.")
        
        results = progress_data['results']
        return render_template('simple_results.html', **results)

@app.route('/chart/<path:filename>')
def serve_chart(filename):
    """Serve chart images"""
    # This is a simplified version - in production you'd want better file handling
    temp_dirs = [d for d in os.listdir(tempfile.gettempdir()) 
                if os.path.isdir(os.path.join(tempfile.gettempdir(), d))]
    
    for temp_dir in temp_dirs:
        full_temp_dir = os.path.join(tempfile.gettempdir(), temp_dir)
        chart_path = os.path.join(full_temp_dir, filename)
        if os.path.exists(chart_path):
            return send_file(chart_path, mimetype='image/png')
    
    return "Chart not found", 404

if __name__ == '__main__':
    print("Starting Simple Bitbucket LOC Analyzer...")
    print("Open your browser to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
