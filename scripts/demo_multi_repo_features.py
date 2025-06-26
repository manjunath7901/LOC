#!/usr/bin/env python3
"""
Demo script showing enhanced multi-repository functionality

This script demonstrates:
1. How multiple repositories generate separate charts
2. Repository name formatting and display
3. Combined analysis features
4. File organization and naming
"""

import sys
import os
from datetime import datetime, timedelta

# Add project paths for imports
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(project_root, 'src'))

def demo_repository_name_formatting():
    """Demonstrate repository name formatting"""
    print("🏷️  Repository Name Formatting Demo")
    print("=" * 50)
    
    test_repositories = [
        "cx-switch-health-read-assist",
        "cx-switch-device-health", 
        "network-automation-tools",
        "api-gateway-service",
        "user-management-system",
        "data-analytics-pipeline"
    ]
    
    print("Repository slug → Display name:")
    for repo_slug in test_repositories:
        # Simple formatting logic (same as in the analyzer)
        display_name = repo_slug.split('-')
        display_name = [word.capitalize() for word in display_name]
        display_name = ' '.join(display_name)
        
        print(f"  {repo_slug:<30} → '{display_name}'")

def demo_multi_repo_chart_separation():
    """Demonstrate how multiple repositories get separate charts"""
    print("\n📊 Multi-Repository Chart Separation Demo")
    print("=" * 50)
    
    example_repos = ["cx-switch-health-read-assist", "cx-switch-device-health"]
    example_user = "manjunath.kallatti@hpe.com"
    
    print(f"📁 Analyzing repositories: {', '.join(example_repos)}")
    print(f"👤 Focus user: {example_user}")
    print(f"📅 Date range: Last 7 days")
    
    print("\n🎯 Expected Individual Repository Outputs:")
    for i, repo in enumerate(example_repos, 1):
        display_name = repo.replace('-', ' ').title()
        print(f"\n  {i}. Repository: {display_name}")
        print(f"     Slug: {repo}")
        print("     Generated files:")
        
        files = [
            f"{repo}_timeline_changes.png",
            f"{repo}_user_contributions.png",
            f"{repo}_summary_dashboard.png",
            f"{repo}_daily_changes.csv",
            f"{repo}_user_contributions.csv"
        ]
        
        for file in files:
            print(f"       📄 {file}")
    
    print(f"\n🔗 Combined Analysis Outputs:")
    combined_files = [
        "combined_analysis_dashboard.png",
        "combined_daily_changes.csv",
        "combined_user_contributions.csv"
    ]
    
    for file in combined_files:
        print(f"     📄 {file}")

def demo_chart_content():
    """Demonstrate what each chart contains"""
    print("\n📈 Chart Content Demonstration")
    print("=" * 50)
    
    charts = {
        "Timeline Changes": {
            "filename": "{repo}_timeline_changes.png",
            "content": [
                "📊 Daily additions and deletions over time",
                "📈 Cumulative changes progression", 
                "🏷️  Repository name prominently displayed in title",
                "👤 User focus indication if specified",
                "📅 Date range clearly shown on x-axis"
            ]
        },
        "User Contributions": {
            "filename": "{repo}_user_contributions.png", 
            "content": [
                "👥 Top contributors ranked by total changes",
                "📊 Additions vs deletions breakdown",
                "🥧 Contribution share pie chart",
                "🏷️  Repository name in chart title",
                "📈 Individual user statistics"
            ]
        },
        "Summary Dashboard": {
            "filename": "{repo}_summary_dashboard.png",
            "content": [
                "📋 Key metrics summary (commits, lines, contributors)",
                "🔥 Activity heatmap by day of week",
                "🏆 Top 5 contributors showcase", 
                "📈 Trend analysis over time",
                "🏷️  Repository name throughout dashboard"
            ]
        },
        "Combined Analysis": {
            "filename": "combined_analysis_dashboard.png",
            "content": [
                "📊 Repository comparison side-by-side",
                "👤 Cross-repository user activity (if focus user specified)",
                "📈 Timeline comparison across all repositories",
                "🔥 Repository activity heatmap",
                "🏷️  All repository names clearly labeled"
            ]
        }
    }
    
    for chart_name, info in charts.items():
        print(f"\n📊 {chart_name}")
        print(f"   File: {info['filename']}")
        print(f"   Contains:")
        for item in info['content']:
            print(f"     • {item}")

def demo_api_workflow():
    """Demonstrate the API workflow"""
    print("\n🌐 API Workflow Demonstration")
    print("=" * 50)
    
    print("1. 🔗 Test Connection")
    print("   POST /api/test-connection")
    print("   → Validates credentials and server connectivity")
    
    print("\n2. 📝 Parse Repository Input")  
    print("   POST /api/repositories/parse")
    print("   → Converts user input to structured repository list")
    
    print("\n3. 🚀 Start Analysis")
    print("   POST /api/analyze")
    print("   → Creates analysis job and returns job ID")
    
    print("\n4. 📊 Monitor Progress")
    print("   GET /api/jobs/{job_id}/status")
    print("   → Returns progress percentage and current status")
    
    print("\n5. 📋 Get Results")
    print("   GET /api/jobs/{job_id}/results")
    print("   → Returns analysis results and file listings")
    
    print("\n6. 📄 Download Files")
    print("   GET /api/files/{filename}")
    print("   → Download individual generated files")

def demo_file_organization():
    """Demonstrate file organization structure"""
    print("\n📁 File Organization Demonstration")
    print("=" * 50)
    
    example_repos = ["cx-switch-health-read-assist", "cx-switch-device-health"]
    
    print("📂 Output Directory Structure:")
    print("output/")
    
    # Individual repository files
    for repo in example_repos:
        display_name = repo.replace('-', ' ').title()
        print(f"├── 📁 {display_name} files:")
        
        files = [
            f"{repo}_timeline_changes.png",
            f"{repo}_user_contributions.png", 
            f"{repo}_summary_dashboard.png",
            f"{repo}_daily_changes.csv",
            f"{repo}_user_contributions.csv"
        ]
        
        for i, file in enumerate(files):
            prefix = "├──" if i < len(files) - 1 else "└──"
            print(f"│   {prefix} 📄 {file}")
        print("│")
    
    # Combined files
    print("├── 📁 Combined Analysis files:")
    combined_files = [
        "combined_analysis_dashboard.png",
        "combined_daily_changes.csv", 
        "combined_user_contributions.csv"
    ]
    
    for i, file in enumerate(combined_files):
        prefix = "├──" if i < len(combined_files) - 1 else "└──"
        print(f"    {prefix} 📄 {file}")

def main():
    """Run all demonstrations"""
    print("🎭 Enhanced Multi-Repository Bitbucket LOC Analyzer")
    print("🎯 Demonstration of Key Features") 
    print("=" * 80)
    
    demo_repository_name_formatting()
    demo_multi_repo_chart_separation()
    demo_chart_content()
    demo_api_workflow()
    demo_file_organization()
    
    print("\n" + "=" * 80)
    print("✨ Key Benefits Demonstrated:")
    print("• 📊 Each repository gets dedicated, clearly-labeled charts")
    print("• 🏷️  Repository names are prominently displayed throughout")
    print("• 🔗 Combined analysis maintains individual repository identity")
    print("• 📁 Well-organized file structure with intuitive naming")
    print("• 🌐 Modern web interface with real-time progress tracking")
    print("• 🧪 Comprehensive API for programmatic access")
    
    print("\n🚀 Next Steps:")
    print("1. Run: ./scripts/start_analyzer.sh")
    print("2. Open frontend/index.html in your browser")
    print("3. Configure analysis with multiple repositories")
    print("4. Observe separate charts generated for each repository")
    print("5. Review the combined analysis dashboard")

if __name__ == "__main__":
    main()
