#!/usr/bin/env python3
"""
Simple Bitbucket LOC Analyzer Web Interface

This restores the original, simple approach that users loved:
- Analyze one or multiple repositories 
- Get separate, clear charts for each repository
- See overall statistics when analyzing multiple repos
- Simple form submission and results display
"""

from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import tempfile
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# Use non-interactive backend
matplotlib.use('Agg')

# Import the original analyzer
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

app = Flask(__name__)

def parse_repo_input(repo_input):
    """Parse repository input - can be comma-separated or line-separated"""
    if not repo_input:
        return []
    
    # Split by newlines or commas and clean up
    repos = []
    for line in repo_input.split('\n'):
        for repo in line.split(','):
            repo = repo.strip()
            if repo:
                repos.append(repo)
    
    return repos

def format_repo_name(repo_slug):
    """Format repository slug for display"""
    return repo_slug.replace('-', ' ').title()

@app.route('/')
def index():
    """Main page with the analysis form"""
    return render_template('simple_index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Handle form submission and start analysis"""
    try:
        # Get form data
        token = request.form.get('token')
        base_url = request.form.get('base_url', 'https://stash.arubanetworks.com')
        workspace = request.form.get('workspace')
        repo_input = request.form.get('repo_slug', '')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        group_by = request.form.get('group_by', 'day')
        focus_user = request.form.get('focus_user', '').strip()
        analysis_type = request.form.get('analysis_type', 'standard')
        
        # Validate required fields
        if not all([token, base_url, workspace, repo_input, start_date, end_date]):
            return render_template('simple_index.html', 
                                 error="Please fill in all required fields")
        
        # Parse repositories
        repos = parse_repo_input(repo_input)
        if not repos:
            return render_template('simple_index.html', 
                                 error="Please enter at least one repository")
        
        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Store analysis configuration
        analysis_results[analysis_id] = {
            'status': 'running',
            'repos': repos,
            'config': {
                'token': token,
                'base_url': base_url,
                'workspace': workspace,
                'start_date': start_date,
                'end_date': end_date,
                'group_by': group_by,
                'focus_user': focus_user if focus_user else None,
                'analysis_type': analysis_type
            },
            'results': {},
            'files': [],
            'progress': 0,
            'message': 'Starting analysis...'
        }
        
        # Start analysis in background thread
        thread = threading.Thread(target=run_analysis, args=(analysis_id,))
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('progress', analysis_id=analysis_id))
        
    except Exception as e:
        return render_template('simple_index.html', 
                             error=f"Error starting analysis: {str(e)}")

def run_analysis(analysis_id):
    """Run the analysis in background"""
    try:
        analysis = analysis_results[analysis_id]
        config = analysis['config']
        repos = analysis['repos']
        
        # Create analyzer
        analyzer = BitbucketLOCAnalyzer(
            config['token'],
            config['base_url'], 
            config['workspace']
        )
        
        total_repos = len(repos)
        
        # Analyze each repository
        for i, repo_slug in enumerate(repos):
            analysis['progress'] = int((i / total_repos) * 80)  # 80% for individual repos
            analysis['message'] = f'Analyzing repository {i+1}/{total_repos}: {repo_slug}'
            
            try:
                # Analyze repository
                if config['focus_user']:
                    daily_data, user_data = analyzer.analyze_repository(
                        repo_slug, 
                        config['start_date'], 
                        config['end_date'],
                        config['group_by'],
                        config['focus_user']
                    )
                else:
                    daily_data, user_data = analyzer.analyze_repository(
                        repo_slug,
                        config['start_date'],
                        config['end_date'], 
                        config['group_by']
                    )
                
                # Create charts for this repository
                repo_display_name = format_repo_name(repo_slug)
                chart_files = create_repo_charts(repo_slug, repo_display_name, daily_data, user_data, config)
                
                # Save data files
                csv_files = save_repo_data(repo_slug, daily_data, user_data)
                
                # Store results
                analysis['results'][repo_slug] = {
                    'display_name': repo_display_name,
                    'daily_data': daily_data,
                    'user_data': user_data,
                    'chart_files': chart_files,
                    'csv_files': csv_files,
                    'summary': {
                        'total_commits': daily_data['commits'].sum() if 'commits' in daily_data else 0,
                        'total_additions': daily_data['additions'].sum() if not daily_data.empty else 0,
                        'total_deletions': daily_data['deletions'].sum() if not daily_data.empty else 0,
                        'contributors': len(user_data) if not user_data.empty else 0
                    }
                }
                
                analysis['files'].extend(chart_files + csv_files)
                
            except Exception as e:
                print(f"Error analyzing repository {repo_slug}: {str(e)}")
                analysis['results'][repo_slug] = {
                    'display_name': format_repo_name(repo_slug),
                    'error': str(e)
                }
        
        # Create combined analysis if multiple repos
        if len(repos) > 1:
            analysis['progress'] = 90
            analysis['message'] = 'Creating combined analysis...'
            
            combined_files = create_combined_analysis(analysis_id)
            analysis['files'].extend(combined_files)
        
        # Complete
        analysis['progress'] = 100
        analysis['status'] = 'completed'
        analysis['message'] = 'Analysis completed successfully!'
        
    except Exception as e:
        analysis['status'] = 'failed'
        analysis['message'] = f'Analysis failed: {str(e)}'
        print(f"Analysis failed for {analysis_id}: {str(e)}")

def create_repo_charts(repo_slug, repo_display_name, daily_data, user_data, config):
    """Create charts for a single repository"""
    chart_files = []
    output_dir = "static/output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Timeline chart
        if not daily_data.empty:
            plt.figure(figsize=(12, 8))
            
            # Convert date column if needed
            if 'date' in daily_data.columns:
                daily_data['date'] = pd.to_datetime(daily_data['date'])
                daily_data = daily_data.sort_values('date')
            
            # Create subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # Daily changes
            dates = daily_data['date'] if 'date' in daily_data.columns else range(len(daily_data))
            additions = daily_data.get('additions', [0] * len(daily_data))
            deletions = daily_data.get('deletions', [0] * len(daily_data))
            
            ax1.bar(dates, additions, alpha=0.7, color='green', label='Additions')
            ax1.bar(dates, [-d for d in deletions], alpha=0.7, color='red', label='Deletions')
            
            title = f'Daily Code Changes - {repo_display_name}'
            if config.get('focus_user'):
                title += f' (User: {config["focus_user"]})'
            
            ax1.set_title(title)
            ax1.set_ylabel('Lines of Code')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Cumulative changes
            cumulative_additions = daily_data['additions'].cumsum() if 'additions' in daily_data else []
            cumulative_deletions = daily_data['deletions'].cumsum() if 'deletions' in daily_data else []
            
            if len(cumulative_additions) > 0:
                ax2.plot(dates, cumulative_additions, color='green', marker='o', label='Cumulative Additions')
                ax2.plot(dates, cumulative_deletions, color='red', marker='s', label='Cumulative Deletions')
                
                ax2.set_title(f'Cumulative Changes - {repo_display_name}')
                ax2.set_ylabel('Cumulative Lines')
                ax2.set_xlabel('Date')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            timeline_file = f"{output_dir}/{repo_slug}_timeline.png"
            plt.savefig(timeline_file, dpi=150, bbox_inches='tight')
            plt.close()
            chart_files.append(timeline_file)
        
        # User contributions chart
        if not user_data.empty:
            plt.figure(figsize=(12, 8))
            
            # Top 10 users
            top_users = user_data.head(10)
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            # Bar chart
            users = top_users['name'] if 'name' in top_users.columns else top_users.index
            additions = top_users.get('additions', [0] * len(top_users))
            deletions = top_users.get('deletions', [0] * len(top_users))
            
            y_pos = range(len(users))
            
            ax1.barh(y_pos, additions, alpha=0.8, color='green', label='Additions')
            ax1.barh(y_pos, [-d for d in deletions], alpha=0.8, color='red', label='Deletions')
            
            ax1.set_yticks(y_pos)
            ax1.set_yticklabels([str(u)[:20] + '...' if len(str(u)) > 20 else str(u) for u in users])
            ax1.set_xlabel('Lines of Code')
            ax1.set_title(f'Top Contributors - {repo_display_name}')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Pie chart for top 5
            if len(top_users) >= 5:
                top_5 = top_users.head(5)
                total_changes = top_5.get('total_changes', top_5.get('additions', []) + top_5.get('deletions', []))
                
                if sum(total_changes) > 0:
                    labels = [str(u)[:15] + '...' if len(str(u)) > 15 else str(u) for u in top_5['name']]
                    ax2.pie(total_changes, labels=labels, autopct='%1.1f%%', startangle=90)
                    ax2.set_title(f'Contribution Share - {repo_display_name}')
            
            plt.tight_layout()
            
            contributors_file = f"{output_dir}/{repo_slug}_contributors.png"
            plt.savefig(contributors_file, dpi=150, bbox_inches='tight')
            plt.close()
            chart_files.append(contributors_file)
            
    except Exception as e:
        print(f"Error creating charts for {repo_slug}: {str(e)}")
    
    return chart_files

def save_repo_data(repo_slug, daily_data, user_data):
    """Save repository data as CSV files"""
    csv_files = []
    output_dir = "static/output"
    
    try:
        if not daily_data.empty:
            daily_file = f"{output_dir}/{repo_slug}_daily_data.csv"
            daily_data.to_csv(daily_file, index=False)
            csv_files.append(daily_file)
        
        if not user_data.empty:
            user_file = f"{output_dir}/{repo_slug}_user_data.csv"
            user_data.to_csv(user_file, index=False)
            csv_files.append(user_file)
            
    except Exception as e:
        print(f"Error saving data for {repo_slug}: {str(e)}")
    
    return csv_files

def create_combined_analysis(analysis_id):
    """Create combined analysis across all repositories"""
    combined_files = []
    output_dir = "static/output"
    
    try:
        analysis = analysis_results[analysis_id]
        results = analysis['results']
        
        # Combine data from all successful repositories
        all_daily_data = []
        all_user_data = []
        
        for repo_slug, repo_result in results.items():
            if 'daily_data' in repo_result and not repo_result['daily_data'].empty:
                daily_copy = repo_result['daily_data'].copy()
                daily_copy['repository'] = repo_result['display_name']
                all_daily_data.append(daily_copy)
            
            if 'user_data' in repo_result and not repo_result['user_data'].empty:
                user_copy = repo_result['user_data'].copy()
                user_copy['repository'] = repo_result['display_name']
                all_user_data.append(user_copy)
        
        if all_daily_data:
            combined_daily = pd.concat(all_daily_data, ignore_index=True)
            combined_file = f"{output_dir}/combined_daily_data.csv"
            combined_daily.to_csv(combined_file, index=False)
            combined_files.append(combined_file)
        
        if all_user_data:
            combined_users = pd.concat(all_user_data, ignore_index=True)
            combined_file = f"{output_dir}/combined_user_data.csv"
            combined_users.to_csv(combined_file, index=False)
            combined_files.append(combined_file)
        
        # Create combined visualization
        if all_daily_data:
            plt.figure(figsize=(15, 10))
            
            # Repository comparison
            repo_summary = combined_daily.groupby('repository').agg({
                'additions': 'sum',
                'deletions': 'sum',
                'commits': 'sum'
            }).reset_index()
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
            
            # Repository comparison
            repos = repo_summary['repository']
            x_pos = range(len(repos))
            width = 0.25
            
            ax1.bar([i - width for i in x_pos], repo_summary['additions'], width, 
                   label='Additions', color='green', alpha=0.8)
            ax1.bar(x_pos, repo_summary['deletions'], width,
                   label='Deletions', color='red', alpha=0.8)
            ax1.bar([i + width for i in x_pos], repo_summary['commits'], width,
                   label='Commits', color='blue', alpha=0.8)
            
            ax1.set_xlabel('Repository')
            ax1.set_ylabel('Count')
            ax1.set_title('Repository Comparison')
            ax1.set_xticks(x_pos)
            ax1.set_xticklabels([repo[:15] + '...' if len(repo) > 15 else repo for repo in repos], rotation=45)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Combined timeline
            for repo in repos:
                repo_data = combined_daily[combined_daily['repository'] == repo]
                if not repo_data.empty and 'date' in repo_data.columns:
                    dates = pd.to_datetime(repo_data['date'])
                    ax2.plot(dates, repo_data['additions'], marker='o', label=f'{repo} (Additions)')
            
            ax2.set_title('Timeline Comparison')
            ax2.set_ylabel('Additions')
            ax2.set_xlabel('Date')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # Summary statistics
            total_additions = repo_summary['additions'].sum()
            total_deletions = repo_summary['deletions'].sum()
            total_commits = repo_summary['commits'].sum()
            
            ax3.bar(['Total Additions', 'Total Deletions', 'Total Commits'],
                   [total_additions, total_deletions, total_commits],
                   color=['green', 'red', 'blue'], alpha=0.7)
            ax3.set_title('Overall Statistics')
            ax3.set_ylabel('Count')
            
            # Repository pie chart
            if len(repo_summary) > 1:
                ax4.pie(repo_summary['additions'], labels=repos, autopct='%1.1f%%', startangle=90)
                ax4.set_title('Additions Distribution by Repository')
            
            plt.tight_layout()
            
            combined_chart_file = f"{output_dir}/combined_analysis.png"
            plt.savefig(combined_chart_file, dpi=150, bbox_inches='tight')
            plt.close()
            combined_files.append(combined_chart_file)
        
    except Exception as e:
        print(f"Error creating combined analysis: {str(e)}")
    
    return combined_files

@app.route('/progress/<analysis_id>')
def progress(analysis_id):
    """Show progress page"""
    if analysis_id not in analysis_results:
        return "Analysis not found", 404
    
    analysis = analysis_results[analysis_id]
    return render_template('progress.html', 
                         analysis_id=analysis_id,
                         analysis=analysis)

@app.route('/status/<analysis_id>')
def status(analysis_id):
    """API endpoint for progress updates"""
    if analysis_id not in analysis_results:
        return jsonify({'error': 'Analysis not found'}), 404
    
    analysis = analysis_results[analysis_id]
    return jsonify({
        'status': analysis['status'],
        'progress': analysis['progress'],
        'message': analysis['message']
    })

@app.route('/results/<analysis_id>')
def results(analysis_id):
    """Show results page"""
    if analysis_id not in analysis_results:
        return "Analysis not found", 404
    
    analysis = analysis_results[analysis_id]
    
    if analysis['status'] != 'completed':
        return redirect(url_for('progress', analysis_id=analysis_id))
    
    return render_template('results.html',
                         analysis_id=analysis_id,
                         analysis=analysis)

@app.route('/download/<path:filename>')
def download(filename):
    """Download generated files"""
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return f"File not found: {str(e)}", 404

if __name__ == '__main__':
    os.makedirs('static/output', exist_ok=True)
    print("🚀 Starting Simple Bitbucket LOC Analyzer")
    print("📊 Features:")
    print("   - Individual repository analysis with separate charts")
    print("   - Multiple repository support") 
    print("   - Combined cross-repository analysis")
    print("   - User-focused analysis")
    print("🌐 Server will be available at: http://localhost:5000")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
