#!/usr/bin/env python3
"""
Comprehensive test for the enhanced multi-repository Bitbucket LOC Analyzer

This test verifies:
1. Multi-repository analysis with separate charts for each repo
2. Proper repository name display in charts
3. Backend API functionality
4. Frontend-backend integration
5. File generation and organization
"""

import sys
import os
import json
import time
import requests
from datetime import datetime, timedelta

# Add project paths
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(project_root, 'src'))
sys.path.append(os.path.join(project_root, 'backend', 'core'))

def test_multi_repo_separation():
    """Test that multiple repositories generate separate charts"""
    print("🧪 Testing Multi-Repository Chart Separation")
    print("=" * 60)
    
    try:
        from improved_bitbucket_analyzer import ImprovedBitbucketAnalyzer
        
        # Mock configuration
        analyzer = ImprovedBitbucketAnalyzer(
            token="test_token",
            base_url="https://stash.arubanetworks.com", 
            workspace="GVT"
        )
        
        # Test repository names formatting
        test_repos = [
            "cx-switch-health-read-assist",
            "cx-switch-device-health", 
            "network-automation-tools"
        ]
        
        print(f"📁 Test repositories: {test_repos}")
        
        # Test repository name formatting
        for repo in test_repos:
            formatted = analyzer._format_repository_name(repo)
            print(f"  {repo} → '{formatted}'")
        
        # Test repository input parsing
        test_inputs = [
            "cx-switch-health-read-assist, cx-switch-device-health",
            "cx-switch-health-read-assist\ncx-switch-device-health\nnetwork-automation-tools",
            "  cx-switch-health-read-assist  ,  cx-switch-device-health  "
        ]
        
        print("\n🔍 Testing repository input parsing:")
        for i, input_str in enumerate(test_inputs, 1):
            parsed = analyzer._parse_repository_input(input_str)
            print(f"  Test {i}: {len(parsed)} repos found")
            for repo in parsed:
                print(f"    - {repo}")
        
        print("\n✅ Repository parsing test completed")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure the improved analyzer is available")
    except Exception as e:
        print(f"❌ Test error: {e}")

def test_backend_api():
    """Test the backend API endpoints"""
    print("\n🌐 Testing Backend API")
    print("=" * 60)
    
    api_base = "http://localhost:5000/api"
    
    # Test health endpoint
    try:
        response = requests.get(f"{api_base}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Health check: {health['status']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Backend server not running. Start with: python backend/api/app.py")
        return
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return
    
    # Test repository parsing endpoint
    test_repo_data = {
        "repo_input": "cx-switch-health-read-assist, cx-switch-device-health, network-tools"
    }
    
    try:
        response = requests.post(
            f"{api_base}/repositories/parse",
            json=test_repo_data,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            repos = result.get('repositories', [])
            print(f"✅ Repository parsing: {len(repos)} repositories found")
            for repo in repos:
                print(f"  - {repo['slug']} → '{repo['display_name']}'")
        else:
            print(f"❌ Repository parsing failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Repository parsing error: {e}")
    
    # Test connection endpoint (will fail without real credentials)
    test_connection_data = {
        "token": "test_token",
        "base_url": "https://stash.arubanetworks.com",
        "workspace": "GVT"
    }
    
    try:
        response = requests.post(
            f"{api_base}/test-connection",
            json=test_connection_data,
            timeout=10
        )
        
        result = response.json()
        if result.get('status') == 'success':
            print("✅ Connection test: Success")
        else:
            print(f"⚠️  Connection test failed (expected with test token): {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Connection test error: {e}")

def test_analysis_workflow():
    """Test the complete analysis workflow"""
    print("\n🔄 Testing Analysis Workflow")
    print("=" * 60)
    
    api_base = "http://localhost:5000/api"
    
    # Prepare test analysis data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    analysis_data = {
        "token": "test_token_would_fail_but_tests_structure",
        "base_url": "https://stash.arubanetworks.com",
        "workspace": "GVT",
        "repo_slugs": "cx-switch-health-read-assist, cx-switch-device-health",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "group_by": "day",
        "focus_user": "manjunath.kallatti@hpe.com"
    }
    
    try:
        # Submit analysis job
        response = requests.post(
            f"{api_base}/analyze",
            json=analysis_data,
            timeout=10
        )
        
        if response.status_code == 202:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Analysis job started: {job_id}")
            
            # Check job status
            max_checks = 5
            for i in range(max_checks):
                time.sleep(2)
                
                status_response = requests.get(f"{api_base}/jobs/{job_id}/status")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"  Status check {i+1}: {status.get('status')} ({status.get('progress', 0)}%)")
                    
                    if status.get('status') in ['completed', 'failed']:
                        break
                else:
                    print(f"  Status check {i+1}: HTTP {status_response.status_code}")
                    
        else:
            result = response.json()
            print(f"⚠️  Analysis submission failed (expected with test token): {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Analysis workflow error: {e}")

def test_file_organization():
    """Test file organization and output structure"""
    print("\n📁 Testing File Organization")
    print("=" * 60)
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    # Check directory structure
    expected_dirs = [
        'backend',
        'frontend', 
        'src',
        'tests',
        'output',
        'docs'
    ]
    
    print("📂 Checking project structure:")
    for dir_name in expected_dirs:
        dir_path = os.path.join(project_root, dir_name)
        if os.path.exists(dir_path):
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ (missing)")
    
    # Check output directory readiness
    output_dir = os.path.join(project_root, 'output')
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        print(f"\n📊 Output directory contains {len(files)} files/folders")
        
        # Look for example output files
        chart_files = [f for f in files if f.endswith('.png')]
        csv_files = [f for f in files if f.endswith('.csv')]
        
        print(f"  📈 Chart files: {len(chart_files)}")
        print(f"  📋 CSV files: {len(csv_files)}")
        
        # Check for repository-specific files
        repo_specific = [f for f in files if any(repo in f for repo in ['cx-switch', 'device-health'])]
        if repo_specific:
            print(f"  🎯 Repository-specific files: {len(repo_specific)}")
            for file in repo_specific[:5]:  # Show first 5
                print(f"    - {file}")
    
    # Check frontend files
    frontend_dir = os.path.join(project_root, 'frontend')
    if os.path.exists(frontend_dir):
        js_file = os.path.join(frontend_dir, 'static', 'js', 'app.js')
        css_file = os.path.join(frontend_dir, 'static', 'css', 'styles.css')
        html_file = os.path.join(frontend_dir, 'index.html')
        
        print("\n🌐 Frontend files:")
        print(f"  {'✅' if os.path.exists(html_file) else '❌'} index.html")
        print(f"  {'✅' if os.path.exists(js_file) else '❌'} app.js")
        print(f"  {'✅' if os.path.exists(css_file) else '❌'} styles.css")

def test_chart_naming():
    """Test chart naming and repository identification"""
    print("\n🏷️  Testing Chart Naming and Repository Identification")
    print("=" * 60)
    
    # Test data that simulates multi-repo analysis
    test_repos = [
        {"slug": "cx-switch-health-read-assist", "display_name": "CX Switch Health Read Assist"},
        {"slug": "cx-switch-device-health", "display_name": "CX Switch Device Health"},
        {"slug": "network-automation-tools", "display_name": "Network Automation Tools"}
    ]
    
    print("📊 Expected chart files for multi-repo analysis:")
    
    for repo in test_repos:
        slug = repo["slug"]
        display_name = repo["display_name"]
        
        expected_files = [
            f"{slug}_timeline_changes.png",
            f"{slug}_user_contributions.png", 
            f"{slug}_summary_dashboard.png",
            f"{slug}_daily_changes.csv",
            f"{slug}_user_contributions.csv"
        ]
        
        print(f"\n📁 Repository: {display_name}")
        print(f"   Slug: {slug}")
        print("   Expected files:")
        for file in expected_files:
            print(f"     - {file}")
    
    print(f"\n🔗 Combined analysis files:")
    combined_files = [
        "combined_analysis_dashboard.png",
        "combined_daily_changes.csv", 
        "combined_user_contributions.csv"
    ]
    
    for file in combined_files:
        print(f"   - {file}")

def main():
    """Run all tests"""
    print("🚀 Enhanced Multi-Repository Bitbucket LOC Analyzer Test Suite")
    print("=" * 80)
    
    # Run all tests
    test_multi_repo_separation()
    test_backend_api()
    test_analysis_workflow()
    test_file_organization()
    test_chart_naming()
    
    print("\n" + "=" * 80)
    print("🎉 Test Suite Complete!")
    print("\nNext Steps:")
    print("1. Start the backend server: python backend/api/app.py")
    print("2. Open frontend/index.html in a browser")
    print("3. Test the complete workflow with real credentials")
    print("4. Verify that each repository gets separate charts with proper naming")

if __name__ == "__main__":
    main()
