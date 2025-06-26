#!/usr/bin/env python3
"""
Improved Bitbucket LOC Analyzer Web UI

This improved version properly handles multiple repositories by creating separate
charts and clearly identifying each repository in the output.
"""

from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import os
import tempfile
import datetime
import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import threading
import time
from typing import List, Dict, Optional

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer
from improved_bitbucket_analyzer import ImprovedBitbucketAnalyzer

app = Flask(__name__)

# Global variables for progress tracking
_analysis_status = {}
_cache_lock = threading.Lock()

def update_analysis_status(analysis_id: str, message: str, progress: int):
    """Update the status of a running analysis"""
    with _cache_lock:
        _analysis_status[analysis_id] = {
            'message': message,
            'progress': progress,
            'timestamp': datetime.datetime.now()
        }

def get_analysis_status(analysis_id: str) -> Dict:
    """Get the current status of an analysis"""
    with _cache_lock:
        return _analysis_status.get(analysis_id, {
            'message': 'Analysis not found',
            'progress': 0,
            'timestamp': datetime.datetime.now()
        })

@app.route('/')
def index():
    """Main page with improved form"""
    return render_template('improved_index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Handle analysis request with improved multi-repo support"""
    
    # Get form data
    token = request.form.get('token')
    base_url = request.form.get('base_url', 'https://stash.arubanetworks.com')
    workspace = request.form.get('workspace')
    repo_slugs_str = request.form.get('repo_slug', '')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    group_by = request.form.get('group_by', 'day')
    analysis_type = request.form.get('analysis_type', 'standard')
    focus_user = request.form.get('focus_user', '').strip()
    
    # Validate required fields
    required_fields = {
        'token': token,
        'workspace': workspace,
        'repo_slug': repo_slugs_str,
        'start_date': start_date,
        'end_date': end_date
    }
    
    missing_fields = [field for field, value in required_fields.items() if not value]
    if missing_fields:
        return render_template('improved_index.html', 
                             error=f"Missing required fields: {', '.join(missing_fields)}")
    
    # Parse repository slugs (support comma-separated values)
    repo_slugs = [slug.strip() for slug in repo_slugs_str.split(',') if slug.strip()]
    if not repo_slugs:
        return render_template('improved_index.html', 
                             error="At least one repository slug is required")
    
    # Generate analysis ID
    analysis_id = f"analysis_{int(time.time())}_{len(repo_slugs)}repos"
    
    # Start analysis in background thread
    analysis_thread = threading.Thread(
        target=run_improved_analysis,
        args=(analysis_id, token, base_url, workspace, repo_slugs, 
              start_date, end_date, group_by, focus_user if focus_user else None)
    )
    analysis_thread.daemon = True
    analysis_thread.start()
    
    # Redirect to results page
    return redirect(url_for('results', analysis_id=analysis_id))

def run_improved_analysis(analysis_id: str, token: str, base_url: str, workspace: str, 
                         repo_slugs: List[str], start_date: str, end_date: str, 
                         group_by: str, focus_user: Optional[str]):
    """Run the improved analysis in a background thread"""
    
    try:
        update_analysis_status(analysis_id, f"Initializing analysis for {len(repo_slugs)} repositories...", 10)
        
        # Create improved analyzer
        analyzer = ImprovedBitbucketAnalyzer(token, base_url, workspace)
        
        update_analysis_status(analysis_id, "Fetching repository data...", 30)
        
        # Run analysis
        results = analyzer.analyze_multiple_repositories(
            repo_slugs, start_date, end_date, group_by, focus_user
        )
        
        if not results:
            update_analysis_status(analysis_id, "No data found for the specified criteria", 0)
            return
        
        update_analysis_status(analysis_id, "Generating charts and reports...", 80)
        
        # Generate summary report
        generate_summary_report(analysis_id, results, focus_user)
        
        update_analysis_status(analysis_id, f"Analysis complete! Processed {len(results)} repositories", 100)
        
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        print(f"Error in analysis {analysis_id}: {error_msg}")
        update_analysis_status(analysis_id, error_msg, 0)

def generate_summary_report(analysis_id: str, results: Dict, focus_user: Optional[str]):
    """Generate a comprehensive summary report"""
    
    # Create summary file
    summary_file = f"output/analysis_{analysis_id}_summary.md"
    
    with open(summary_file, 'w') as f:
        f.write(f"# Analysis Summary Report\n\n")
        f.write(f"**Analysis ID:** {analysis_id}\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Repositories Analyzed:** {len(results)}\n")
        if focus_user:
            f.write(f"**Focus User:** {focus_user}\n")
        f.write(f"\n---\n\n")
        
        # Repository summaries
        f.write(f"## Repository Analysis\n\n")
        
        for repo_slug, data in results.items():
            daily_data = data['daily_data']
            user_data = data['user_data']
            
            total_additions = daily_data['additions'].sum()
            total_deletions = daily_data['deletions'].sum()
            total_commits = daily_data['commits'].sum() if 'commits' in daily_data.columns else 0
            contributors = len(user_data)
            
            f.write(f"### 📁 {repo_slug}\n\n")
            f.write(f"- **Total Additions:** {total_additions:,} lines\n")
            f.write(f"- **Total Deletions:** {total_deletions:,} lines\n")
            f.write(f"- **Net Change:** {total_additions - total_deletions:,} lines\n")
            f.write(f"- **Total Commits:** {total_commits:,}\n")
            f.write(f"- **Contributors:** {contributors}\n")
            f.write(f"- **Active Days:** {len(daily_data[daily_data['commits'] > 0]) if 'commits' in daily_data.columns else 'N/A'}\n")
            
            # Top contributors for this repo
            if not user_data.empty:
                f.write(f"\n**Top Contributors:**\n")
                top_5 = user_data.head(5)
                for i, (_, contributor) in enumerate(top_5.iterrows(), 1):
                    name = contributor.get('name', 'Unknown')
                    changes = contributor.get('total_changes', 0)
                    commits = contributor.get('commits', 0)
                    f.write(f"{i}. {name}: {changes:,} changes, {commits} commits\n")
            
            f.write(f"\n**Generated Files:**\n")
            f.write(f"- Timeline Chart: `{repo_slug}_timeline_changes.png`\n")
            f.write(f"- User Contributions: `{repo_slug}_user_contributions.png`\n")
            f.write(f"- Summary Dashboard: `{repo_slug}_summary_dashboard.png`\n")
            f.write(f"- Daily Data: `{repo_slug}_daily_changes.csv`\n")
            f.write(f"- User Data: `{repo_slug}_user_contributions.csv`\n\n")
        
        # Combined analysis section
        if len(results) > 1:
            f.write(f"## Combined Analysis\n\n")
            f.write(f"**Multi-Repository Files:**\n")
            f.write(f"- Combined Dashboard: `combined_analysis_dashboard.png`\n")
            f.write(f"- Combined Daily Data: `combined_daily_changes.csv`\n")
            f.write(f"- Combined User Data: `combined_user_contributions.csv`\n\n")
        
        f.write(f"---\n\n")
        f.write(f"*Report generated by Improved Bitbucket LOC Analyzer*\n")

@app.route('/results/<analysis_id>')
def results(analysis_id):
    """Display analysis results with improved multi-repo visualization"""
    
    status = get_analysis_status(analysis_id)
    
    if status['progress'] < 100:
        return render_template('improved_results.html', 
                             analysis_id=analysis_id,
                             status=status,
                             completed=False)
    
    # Get list of generated files
    output_dir = "output"
    files = []
    charts = []
    data_files = []
    
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if analysis_id in filename or not analysis_id.startswith('analysis_'):
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path):
                    if filename.endswith('.png'):
                        charts.append(filename)
                    elif filename.endswith('.csv'):
                        data_files.append(filename)
                    files.append(filename)
    
    # Group charts by repository
    repo_charts = {}
    combined_charts = []
    
    for chart in charts:
        if 'combined_' in chart:
            combined_charts.append(chart)
        else:
            # Extract repo name from filename
            repo_name = chart.split('_')[0] if '_' in chart else 'unknown'
            if repo_name not in repo_charts:
                repo_charts[repo_name] = []
            repo_charts[repo_name].append(chart)
    
    return render_template('improved_results.html',
                         analysis_id=analysis_id,
                         status=status,
                         completed=True,
                         files=files,
                         repo_charts=repo_charts,
                         combined_charts=combined_charts,
                         data_files=data_files)

@app.route('/status/<analysis_id>')
def status(analysis_id):
    """API endpoint for getting analysis status"""
    return jsonify(get_analysis_status(analysis_id))

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated files"""
    file_path = os.path.join('output', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404

@app.route('/view/<filename>')
def view_file(filename):
    """View generated files in browser"""
    file_path = os.path.join('output', filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        return "File not found", 404

if __name__ == '__main__':
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)
    
    print("🚀 Starting Improved Bitbucket LOC Analyzer Web UI")
    print("📊 Features:")
    print("   - Multi-repository analysis")
    print("   - Separate charts per repository") 
    print("   - Combined cross-repository analysis")
    print("   - Improved project structure")
    print("   - Real-time progress tracking")
    print("\n🌐 Access at: http://127.0.0.1:5000")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
