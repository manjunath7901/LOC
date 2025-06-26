#!/usr/bin/env python3
"""
Flask API Backend for Multi-Repository Bitbucket LOC Analyzer

Provides REST API endpoints for repository analysis with proper separation
of concerns and enhanced multi-repository support.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add project paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from multi_repo_analyzer import MultiRepoAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Global storage for analysis status and results
analysis_jobs = {}
job_lock = threading.Lock()

# Configuration
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

class AnalysisJob:
    """Class to track analysis job status and results"""
    
    def __init__(self, job_id: str, config: Dict):
        self.job_id = job_id
        self.config = config
        self.status = "queued"
        self.progress = 0
        self.message = "Analysis queued"
        self.start_time = datetime.now()
        self.end_time = None
        self.results = None
        self.error = None
        self.generated_files = []
    
    def update_status(self, status: str, progress: int, message: str):
        """Update job status"""
        self.status = status
        self.progress = progress
        self.message = message
        if status in ["completed", "failed"]:
            self.end_time = datetime.now()
        
        logger.info(f"Job {self.job_id}: {message} ({progress}%)")
    
    def to_dict(self) -> Dict:
        """Convert job to dictionary for API response"""
        return {
            'job_id': self.job_id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'generated_files': self.generated_files,
            'error': self.error
        }

def parse_repository_input(repo_input: str) -> List[Dict]:
    """
    Parse repository input and create repo configs
    
    Args:
        repo_input: Comma or newline separated repository slugs
        
    Returns:
        List of repository configurations
    """
    # Split by comma or newline and clean up
    repos = []
    for line in repo_input.replace(',', '\n').split('\n'):
        slug = line.strip()
        if slug:
            # Create display name from slug (capitalize and replace hyphens)
            display_name = slug.replace('-', ' ').title()
            repos.append({
                'slug': slug,
                'display_name': display_name
            })
    
    return repos

def run_analysis_job(job: AnalysisJob):
    """
    Run analysis job in background thread
    
    Args:
        job: AnalysisJob instance to execute
    """
    try:
        job.update_status("initializing", 10, "Initializing analyzer...")
        
        config = job.config
        
        # Create analyzer
        analyzer = MultiRepoAnalyzer(
            token=config['token'],
            base_url=config['base_url'],
            workspace=config['workspace'],
            output_dir=OUTPUT_DIR
        )
        
        job.update_status("parsing", 20, "Parsing repository configurations...")
        
        # Parse repositories
        repo_configs = parse_repository_input(config['repo_slugs'])
        
        if not repo_configs:
            job.update_status("failed", 0, "No valid repositories provided")
            return
        
        job.update_status("analyzing", 30, f"Analyzing {len(repo_configs)} repositories...")
        
        # Run analysis
        results = analyzer.analyze_repositories(
            repo_configs=repo_configs,
            start_date=config['start_date'],
            end_date=config['end_date'],
            group_by=config.get('group_by', 'day'),
            focus_user=config.get('focus_user')
        )
        
        job.update_status("finalizing", 90, "Finalizing results...")
        
        # Get generated files
        generated_files = []
        if os.path.exists(OUTPUT_DIR):
            for filename in os.listdir(OUTPUT_DIR):
                if filename.endswith(('.png', '.csv', '.md')):
                    generated_files.append(filename)
        
        job.generated_files = generated_files
        job.results = {
            'repositories_analyzed': len(results),
            'total_files_generated': len(generated_files),
            'repo_results': {
                repo_slug: {
                    'display_name': data['display_name'],
                    'total_commits': data['analysis_meta']['total_commits'],
                    'total_contributors': data['analysis_meta']['total_contributors'],
                    'total_additions': data['analysis_meta']['total_additions'],
                    'total_deletions': data['analysis_meta']['total_deletions']
                }
                for repo_slug, data in results.items()
            }
        }
        
        job.update_status("completed", 100, f"Analysis complete! Generated {len(generated_files)} files")
        
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        job.error = error_msg
        job.update_status("failed", 0, error_msg)
        logger.error(f"Job {job.job_id} failed: {error_msg}")

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """
    Start a new analysis job
    
    Expected JSON payload:
    {
        "token": "bitbucket_token",
        "base_url": "https://stash.example.com",
        "workspace": "PROJECT_KEY",
        "repo_slugs": "repo1, repo2, repo3",
        "start_date": "2025-06-20",
        "end_date": "2025-06-26",
        "group_by": "day",
        "focus_user": "user@example.com"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['token', 'base_url', 'workspace', 'repo_slugs', 'start_date', 'end_date']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create job
        job = AnalysisJob(job_id, data)
        
        # Store job
        with job_lock:
            analysis_jobs[job_id] = job
        
        # Start analysis in background
        analysis_thread = threading.Thread(target=run_analysis_job, args=(job,))
        analysis_thread.daemon = True
        analysis_thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': 'Analysis job started successfully'
        }), 202
        
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        return jsonify({'error': f'Failed to start analysis: {str(e)}'}), 500

@app.route('/api/jobs/<job_id>/status', methods=['GET'])
def get_job_status(job_id: str):
    """Get status of a specific analysis job"""
    
    with job_lock:
        job = analysis_jobs.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job.to_dict())

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all analysis jobs"""
    
    with job_lock:
        jobs = {job_id: job.to_dict() for job_id, job in analysis_jobs.items()}
    
    return jsonify(jobs)

@app.route('/api/jobs/<job_id>/results', methods=['GET'])
def get_job_results(job_id: str):
    """Get detailed results of a completed analysis job"""
    
    with job_lock:
        job = analysis_jobs.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.status != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400
    
    return jsonify({
        'job_id': job_id,
        'results': job.results,
        'generated_files': job.generated_files,
        'status': job.to_dict()
    })

@app.route('/api/files/<filename>', methods=['GET'])
def download_file(filename: str):
    """Download a generated file"""
    
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Security check - only allow files in output directory
    if not os.path.commonpath([OUTPUT_DIR, file_path]) == OUTPUT_DIR:
        return jsonify({'error': 'Access denied'}), 403
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/files/<filename>/view', methods=['GET'])
def view_file(filename: str):
    """View a generated file in browser"""
    
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Security check
    if not os.path.commonpath([OUTPUT_DIR, file_path]) == OUTPUT_DIR:
        return jsonify({'error': 'Access denied'}), 403
    
    return send_file(file_path)

@app.route('/api/repositories/parse', methods=['POST'])
def parse_repositories():
    """
    Parse repository input and return structured configuration
    
    Expected JSON payload:
    {
        "repo_input": "repo1, repo2\\nrepo3"
    }
    """
    try:
        data = request.get_json()
        repo_input = data.get('repo_input', '')
        
        if not repo_input:
            return jsonify({'error': 'No repository input provided'}), 400
        
        repo_configs = parse_repository_input(repo_input)
        
        return jsonify({
            'repositories': repo_configs,
            'count': len(repo_configs)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to parse repositories: {str(e)}'}), 500

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """
    Test connection to Bitbucket server
    
    Expected JSON payload:
    {
        "token": "bitbucket_token",
        "base_url": "https://stash.example.com",
        "workspace": "PROJECT_KEY"
    }
    """
    try:
        data = request.get_json()
        
        required_fields = ['token', 'base_url', 'workspace']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Test connection by creating analyzer
        analyzer = MultiRepoAnalyzer(
            token=data['token'],
            base_url=data['base_url'],
            workspace=data['workspace']
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Connection test successful',
            'workspace': data['workspace'],
            'base_url': data['base_url']
        })
        
    except Exception as e:
        return jsonify({
            'status': 'failed',
            'error': f'Connection test failed: {str(e)}'
        }), 400

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting Multi-Repository Bitbucket LOC Analyzer API Server")
    print("📊 Features:")
    print("   - Multi-repository analysis with separate charts")
    print("   - RESTful API endpoints")
    print("   - Background job processing")
    print("   - Real-time progress tracking")
    print("   - File download and viewing")
    print("   - Enhanced repository naming")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print("\n🌐 API Base URL: http://127.0.0.1:5001")
    print("📖 Available endpoints:")
    print("   GET  /api/health - Health check")
    print("   POST /api/analyze - Start analysis")
    print("   GET  /api/jobs/<id>/status - Job status")
    print("   GET  /api/jobs/<id>/results - Job results")
    print("   GET  /api/files/<filename> - Download file")
    print("   POST /api/test-connection - Test connection")
    
    app.run(debug=True, host='127.0.0.1', port=5001)
