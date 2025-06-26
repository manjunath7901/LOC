#!/usr/bin/env python3
"""
Multi-Repository Bitbucket LOC Analyzer Core

Enhanced analyzer that properly handles multiple repositories with separate
charts for each repository, clear repo identification, and improved structure.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import sys
from typing import List, Dict, Tuple, Optional
import logging

# Configure matplotlib for server environment
import matplotlib
matplotlib.use('Agg')

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import seaborn as sns
    HAS_SEABORN = True
    sns.set_style("whitegrid")
except ImportError:
    HAS_SEABORN = False

from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiRepoAnalyzer:
    """Enhanced multi-repository analyzer with clear separation and organization"""
    
    def __init__(self, token: str, base_url: str, workspace: str, output_dir: str = "output"):
        """
        Initialize the multi-repository analyzer
        
        Args:
            token: Bitbucket authentication token
            base_url: Bitbucket server base URL
            workspace: Workspace/project key
            output_dir: Directory for output files
        """
        self.analyzer = BitbucketLOCAnalyzer(token, base_url, workspace)
        self.output_dir = output_dir
        self.workspace = workspace
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set up plotting style
        self._setup_plotting_style()
        
    def _setup_plotting_style(self):
        """Configure matplotlib plotting style"""
        plt.style.use('default')
        
        # Set font and style preferences
        plt.rcParams.update({
            'figure.facecolor': 'white',
            'axes.facecolor': 'white',
            'font.size': 10,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'axes.grid': True,
            'grid.alpha': 0.3
        })
    
    def analyze_repositories(self, 
                           repo_configs: List[Dict],
                           start_date: str, 
                           end_date: str, 
                           group_by: str = 'day',
                           focus_user: Optional[str] = None) -> Dict:
        """
        Analyze multiple repositories with enhanced configuration
        
        Args:
            repo_configs: List of dicts with 'slug' and 'display_name' keys
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            group_by: Grouping period ('day', 'week', 'month')
            focus_user: Optional user to focus analysis on
            
        Returns:
            Dictionary containing analysis results for each repository
        """
        results = {}
        successful_repos = []
        
        logger.info(f"🔍 Starting analysis of {len(repo_configs)} repositories...")
        
        for i, repo_config in enumerate(repo_configs, 1):
            repo_slug = repo_config['slug']
            display_name = repo_config.get('display_name', repo_slug)
            
            logger.info(f"📊 [{i}/{len(repo_configs)}] Analyzing: {display_name} ({repo_slug})")
            
            try:
                # Analyze individual repository
                daily_data, user_data = self.analyzer.analyze_repository(
                    repo_slug, start_date, end_date, group_by, focus_user
                )
                
                if daily_data.empty or user_data.empty:
                    logger.warning(f"⚠️ No data found for repository: {display_name}")
                    continue
                
                # Store results with enhanced metadata
                results[repo_slug] = {
                    'daily_data': daily_data,
                    'user_data': user_data,
                    'repo_slug': repo_slug,
                    'display_name': display_name,
                    'analysis_meta': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'group_by': group_by,
                        'focus_user': focus_user,
                        'total_commits': daily_data['commits'].sum() if 'commits' in daily_data.columns else 0,
                        'total_contributors': len(user_data),
                        'total_additions': daily_data['additions'].sum(),
                        'total_deletions': daily_data['deletions'].sum()
                    }
                }
                
                # Create repository-specific visualizations
                self._create_repository_visualizations(repo_slug, display_name, daily_data, user_data, focus_user)
                
                # Save repository-specific data
                self._save_repository_data(repo_slug, display_name, daily_data, user_data)
                
                successful_repos.append((repo_slug, display_name))
                logger.info(f"✅ Analysis complete for {display_name}")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing repository {display_name}: {str(e)}")
                continue
        
        # Create combined analysis if multiple successful repositories
        if len(successful_repos) > 1:
            self._create_combined_analysis(results, focus_user)
        
        # Generate comprehensive report
        self._generate_analysis_report(results, focus_user)
        
        logger.info(f"🎉 Analysis complete! Processed {len(successful_repos)} repositories successfully")
        return results
    
    def _create_repository_visualizations(self, 
                                        repo_slug: str,
                                        display_name: str, 
                                        daily_data: pd.DataFrame, 
                                        user_data: pd.DataFrame,
                                        focus_user: Optional[str] = None):
        """Create comprehensive visualizations for a single repository"""
        
        logger.info(f"📈 Creating visualizations for {display_name}")
        
        # 1. Timeline Analysis Chart
        self._create_timeline_chart(repo_slug, display_name, daily_data, focus_user)
        
        # 2. User Contributions Chart
        self._create_user_contributions_chart(repo_slug, display_name, user_data, focus_user)
        
        # 3. Summary Dashboard
        self._create_summary_dashboard(repo_slug, display_name, daily_data, user_data, focus_user)
        
        # 4. Activity Heatmap (if enough data)
        if len(daily_data) > 7:
            self._create_activity_heatmap(repo_slug, display_name, daily_data, focus_user)
    
    def _create_timeline_chart(self, 
                             repo_slug: str,
                             display_name: str, 
                             daily_data: pd.DataFrame,
                             focus_user: Optional[str] = None):
        """Create enhanced timeline chart with repo name prominently displayed"""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Prepare data
        daily_data_copy = daily_data.copy()
        if 'date' in daily_data_copy.columns:
            daily_data_copy['date'] = pd.to_datetime(daily_data_copy['date'])
            daily_data_copy = daily_data_copy.sort_values('date')
        
        dates = daily_data_copy['date']
        additions = daily_data_copy.get('additions', [0] * len(dates))
        deletions = daily_data_copy.get('deletions', [0] * len(dates))
        
        # Chart 1: Daily changes with enhanced styling
        ax1.bar(dates, additions, alpha=0.8, color='#2ecc71', label='Additions', width=0.8)
        ax1.bar(dates, [-d for d in deletions], alpha=0.8, color='#e74c3c', label='Deletions', width=0.8)
        
        # Enhanced title with repo name
        title = f'📈 Daily Code Changes - {display_name}'
        if focus_user:
            title += f'\n👤 Focus: {focus_user}'
        ax1.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('Lines of Code', fontsize=12)
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        
        # Format x-axis
        if len(dates) > 0:
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//8)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Chart 2: Cumulative trends
        cumulative_additions = daily_data_copy['additions'].cumsum()
        cumulative_deletions = daily_data_copy['deletions'].cumsum()
        net_changes = cumulative_additions - cumulative_deletions
        
        ax2.plot(dates, cumulative_additions, color='#2ecc71', marker='o', 
                linewidth=3, markersize=4, label='Cumulative Additions')
        ax2.plot(dates, cumulative_deletions, color='#e74c3c', marker='s', 
                linewidth=3, markersize=4, label='Cumulative Deletions')
        ax2.plot(dates, net_changes, color='#3498db', marker='^', 
                linewidth=3, markersize=4, label='Net Changes')
        
        ax2.set_title(f'📊 Cumulative Trends - {display_name}', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Cumulative Lines', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        if len(dates) > 0:
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//8)))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save with repo-specific filename
        filename = f"{self.output_dir}/{repo_slug}_timeline_analysis.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"📊 Timeline chart saved: {filename}")
    
    def _create_user_contributions_chart(self, 
                                       repo_slug: str,
                                       display_name: str, 
                                       user_data: pd.DataFrame,
                                       focus_user: Optional[str] = None):
        """Create user contributions chart with clear repo identification"""
        
        if user_data.empty:
            return
        
        # Limit to top 12 users for better visibility
        top_users = user_data.head(12).copy()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
        
        # Chart 1: Horizontal bar chart for additions/deletions
        users = top_users['name'] if 'name' in top_users.columns else top_users.index
        additions = top_users.get('additions', [0] * len(users))
        deletions = top_users.get('deletions', [0] * len(users))
        
        y_pos = range(len(users))
        
        # Create horizontal bars
        bars1 = ax1.barh(y_pos, additions, alpha=0.8, color='#2ecc71', label='Additions')
        bars2 = ax1.barh(y_pos, [-d for d in deletions], alpha=0.8, color='#e74c3c', label='Deletions')
        
        # Customize chart
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels([str(u)[:25] + '...' if len(str(u)) > 25 else str(u) for u in users])
        ax1.set_xlabel('Lines of Code', fontsize=12)
        
        title = f'👥 User Contributions - {display_name}'
        if focus_user:
            title += f'\n🎯 Focused on: {focus_user}'
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='x')
        
        # Add value labels on bars
        for bar, value in zip(bars1, additions):
            if value > 0:
                ax1.text(bar.get_width() + max(additions)*0.01, bar.get_y() + bar.get_height()/2,
                        f'+{value:,}', ha='left', va='center', fontsize=8, color='#2ecc71')
        
        for bar, value in zip(bars2, deletions):
            if value > 0:
                ax1.text(-value - max(deletions)*0.01, bar.get_y() + bar.get_height()/2,
                        f'-{value:,}', ha='right', va='center', fontsize=8, color='#e74c3c')
        
        # Chart 2: Contribution distribution pie chart
        if len(top_users) > 0:
            top_10 = top_users.head(10)
            total_changes = top_10.get('total_changes', top_10.get('additions', []) + top_10.get('deletions', []))
            
            if sum(total_changes) > 0:
                labels = [str(u)[:15] + '...' if len(str(u)) > 15 else str(u) for u in top_10['name']]
                
                # Use a nice color palette
                colors = plt.cm.Set3(range(len(labels)))
                
                wedges, texts, autotexts = ax2.pie(total_changes, labels=labels, autopct='%1.1f%%',
                                                  colors=colors, startangle=90)
                
                ax2.set_title(f'📊 Contribution Distribution - {display_name}\n(Top 10 Contributors)', 
                             fontsize=12, fontweight='bold')
                
                # Improve text readability
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                    autotext.set_fontsize(8)
        
        plt.tight_layout()
        
        # Save with repo-specific filename
        filename = f"{self.output_dir}/{repo_slug}_user_contributions.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"👥 User contributions chart saved: {filename}")
    
    def _create_summary_dashboard(self, 
                                repo_slug: str,
                                display_name: str, 
                                daily_data: pd.DataFrame, 
                                user_data: pd.DataFrame,
                                focus_user: Optional[str] = None):
        """Create comprehensive summary dashboard"""
        
        fig = plt.figure(figsize=(20, 12))
        
        # Create a grid layout
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # Main title
        fig.suptitle(f'📋 Repository Dashboard - {display_name}', 
                    fontsize=20, fontweight='bold', y=0.95)
        
        # Calculate summary statistics
        total_additions = daily_data['additions'].sum() if not daily_data.empty else 0
        total_deletions = daily_data['deletions'].sum() if not daily_data.empty else 0
        total_commits = daily_data['commits'].sum() if 'commits' in daily_data.columns and not daily_data.empty else 0
        active_days = len(daily_data[daily_data['commits'] > 0]) if not daily_data.empty and 'commits' in daily_data.columns else 0
        unique_contributors = len(user_data) if not user_data.empty else 0
        avg_changes_per_day = (total_additions + total_deletions) / len(daily_data) if not daily_data.empty else 0
        
        # 1. Key Metrics (top row)
        ax1 = fig.add_subplot(gs[0, :])
        metrics = ['Total\nAdditions', 'Total\nDeletions', 'Net\nChanges', 'Total\nCommits', 'Active\nDays', 'Contributors']
        values = [total_additions, total_deletions, total_additions - total_deletions, 
                 total_commits, active_days, unique_contributors]
        colors = ['#2ecc71', '#e74c3c', '#3498db', '#9b59b6', '#f39c12', '#1abc9c']
        
        bars = ax1.bar(metrics, values, color=colors, alpha=0.8)
        ax1.set_title('📊 Key Metrics Overview', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Count')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                    f'{value:,}', ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        # 2. Daily Activity Trend (middle left)
        ax2 = fig.add_subplot(gs[1, :2])
        if not daily_data.empty and len(daily_data) > 1:
            dates = pd.to_datetime(daily_data['date'])
            ax2.plot(dates, daily_data['additions'], color='#2ecc71', marker='o', 
                    linewidth=2, label='Additions')
            ax2.plot(dates, daily_data['deletions'], color='#e74c3c', marker='s', 
                    linewidth=2, label='Deletions')
            
            ax2.set_title('📈 Daily Activity Trend', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Lines of Code')
            ax2.set_xlabel('Date')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # Format dates
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # 3. Top Contributors (middle right)
        ax3 = fig.add_subplot(gs[1, 2:])
        if not user_data.empty:
            top_5 = user_data.head(5)
            contributors = [str(name)[:20] + '...' if len(str(name)) > 20 else str(name) 
                          for name in top_5['name']]
            contributions = top_5.get('total_changes', top_5.get('additions', [0] * len(contributors)))
            
            bars = ax3.barh(contributors, contributions, color='#3498db', alpha=0.8)
            ax3.set_title('🏆 Top 5 Contributors', fontsize=12, fontweight='bold')
            ax3.set_xlabel('Total Changes')
            
            # Add value labels
            for bar, value in zip(bars, contributions):
                ax3.text(bar.get_width() + max(contributions)*0.01, bar.get_y() + bar.get_height()/2,
                        f'{value:,}', ha='left', va='center', fontweight='bold', fontsize=9)
        
        # 4. Activity Distribution (bottom left)
        ax4 = fig.add_subplot(gs[2, :2])
        if not daily_data.empty and 'commits' in daily_data.columns:
            commit_counts = daily_data['commits'].value_counts().sort_index()
            ax4.bar(commit_counts.index, commit_counts.values, color='#f39c12', alpha=0.8)
            ax4.set_title('📊 Commits per Day Distribution', fontsize=12, fontweight='bold')
            ax4.set_xlabel('Commits per Day')
            ax4.set_ylabel('Number of Days')
            ax4.grid(True, alpha=0.3)
        
        # 5. Weekly Activity Pattern (bottom right)
        ax5 = fig.add_subplot(gs[2, 2:])
        if not daily_data.empty and len(daily_data) > 7:
            daily_data_copy = daily_data.copy()
            daily_data_copy['weekday'] = pd.to_datetime(daily_data_copy['date']).dt.day_name()
            weekday_activity = daily_data_copy.groupby('weekday')['additions'].sum()
            
            # Reorder days
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_activity = weekday_activity.reindex([day for day in day_order if day in weekday_activity.index])
            
            ax5.bar(range(len(weekday_activity)), weekday_activity.values, color='#9b59b6', alpha=0.8)
            ax5.set_title('📅 Weekly Activity Pattern', fontsize=12, fontweight='bold')
            ax5.set_xlabel('Day of Week')
            ax5.set_ylabel('Total Additions')
            ax5.set_xticks(range(len(weekday_activity)))
            ax5.set_xticklabels([day[:3] for day in weekday_activity.index], rotation=45)
            ax5.grid(True, alpha=0.3)
        
        # Save dashboard
        filename = f"{self.output_dir}/{repo_slug}_summary_dashboard.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"📋 Summary dashboard saved: {filename}")
    
    def _create_activity_heatmap(self, 
                               repo_slug: str,
                               display_name: str, 
                               daily_data: pd.DataFrame,
                               focus_user: Optional[str] = None):
        """Create activity heatmap for the repository"""
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Prepare data for heatmap
        daily_data_copy = daily_data.copy()
        daily_data_copy['date'] = pd.to_datetime(daily_data_copy['date'])
        daily_data_copy['weekday'] = daily_data_copy['date'].dt.day_name()
        daily_data_copy['week'] = daily_data_copy['date'].dt.isocalendar().week
        
        # Create pivot table
        heatmap_data = daily_data_copy.pivot_table(
            values='commits', 
            index='weekday', 
            columns='week', 
            aggfunc='sum', 
            fill_value=0
        )
        
        # Reorder weekdays
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = heatmap_data.reindex([day for day in weekday_order if day in heatmap_data.index])
        
        # Create heatmap
        if HAS_SEABORN:
            sns.heatmap(heatmap_data, ax=ax, cmap='YlOrRd', annot=True, fmt='g', 
                       cbar_kws={'label': 'Commits'})
        else:
            im = ax.imshow(heatmap_data.values, cmap='YlOrRd', aspect='auto')
            ax.set_xticks(range(len(heatmap_data.columns)))
            ax.set_yticks(range(len(heatmap_data.index)))
            ax.set_xticklabels(heatmap_data.columns)
            ax.set_yticklabels(heatmap_data.index)
            plt.colorbar(im, ax=ax, label='Commits')
        
        # Customize
        title = f'🔥 Activity Heatmap - {display_name}'
        if focus_user:
            title += f' (User: {focus_user})'
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Week Number')
        ax.set_ylabel('Day of Week')
        
        plt.tight_layout()
        
        # Save heatmap
        filename = f"{self.output_dir}/{repo_slug}_activity_heatmap.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"🔥 Activity heatmap saved: {filename}")
    
    def _save_repository_data(self, 
                            repo_slug: str,
                            display_name: str, 
                            daily_data: pd.DataFrame, 
                            user_data: pd.DataFrame):
        """Save repository data with enhanced metadata"""
        
        # Add metadata to data
        daily_data_enhanced = daily_data.copy()
        user_data_enhanced = user_data.copy()
        
        daily_data_enhanced['repository_slug'] = repo_slug
        daily_data_enhanced['repository_name'] = display_name
        daily_data_enhanced['workspace'] = self.workspace
        
        user_data_enhanced['repository_slug'] = repo_slug
        user_data_enhanced['repository_name'] = display_name
        user_data_enhanced['workspace'] = self.workspace
        
        # Save CSV files with enhanced names
        daily_filename = f"{self.output_dir}/{repo_slug}_daily_data.csv"
        user_filename = f"{self.output_dir}/{repo_slug}_user_data.csv"
        
        daily_data_enhanced.to_csv(daily_filename, index=False)
        user_data_enhanced.to_csv(user_filename, index=False)
        
        logger.info(f"💾 Data saved: {daily_filename}, {user_filename}")
    
    def _create_combined_analysis(self, results: Dict, focus_user: Optional[str] = None):
        """Create combined analysis across all repositories"""
        
        logger.info("🔗 Creating combined multi-repository analysis...")
        
        # Combine all data
        all_daily_data = []
        all_user_data = []
        repo_names = []
        
        for repo_slug, data in results.items():
            daily_data = data['daily_data'].copy()
            user_data = data['user_data'].copy()
            display_name = data['display_name']
            
            daily_data['repository_slug'] = repo_slug
            daily_data['repository_name'] = display_name
            user_data['repository_slug'] = repo_slug  
            user_data['repository_name'] = display_name
            
            all_daily_data.append(daily_data)
            all_user_data.append(user_data)
            repo_names.append(display_name)
        
        if all_daily_data and all_user_data:
            combined_daily = pd.concat(all_daily_data, ignore_index=True)
            combined_users = pd.concat(all_user_data, ignore_index=True)
            
            # Create combined visualization
            self._create_combined_dashboard(combined_daily, combined_users, repo_names, focus_user)
            
            # Save combined data
            combined_daily.to_csv(f"{self.output_dir}/combined_daily_analysis.csv", index=False)
            combined_users.to_csv(f"{self.output_dir}/combined_user_analysis.csv", index=False)
            
            logger.info("✅ Combined analysis complete!")
    
    def _create_combined_dashboard(self, 
                                 combined_daily: pd.DataFrame, 
                                 combined_users: pd.DataFrame, 
                                 repo_names: List[str],
                                 focus_user: Optional[str] = None):
        """Create comprehensive combined dashboard"""
        
        fig = plt.figure(figsize=(24, 16))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Main title
        title = f'🔗 Multi-Repository Analysis Dashboard - {len(repo_names)} Repositories'
        if focus_user:
            title += f'\n👤 Focus: {focus_user}'
        fig.suptitle(title, fontsize=22, fontweight='bold', y=0.95)
        
        # 1. Repository Comparison (top row, spans 2 columns)
        ax1 = fig.add_subplot(gs[0, :2])
        repo_summary = combined_daily.groupby('repository_name').agg({
            'additions': 'sum',
            'deletions': 'sum',
            'commits': 'sum'
        }).reset_index()
        
        x = range(len(repo_summary))
        width = 0.25
        
        ax1.bar([i - width for i in x], repo_summary['additions'], width, 
               label='Additions', color='#2ecc71', alpha=0.8)
        ax1.bar(x, repo_summary['deletions'], width, 
               label='Deletions', color='#e74c3c', alpha=0.8)
        ax1.bar([i + width for i in x], repo_summary['commits'], width, 
               label='Commits', color='#3498db', alpha=0.8)
        
        ax1.set_xlabel('Repository')
        ax1.set_ylabel('Count')
        ax1.set_title('📊 Repository Comparison', fontsize=14, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels([name[:20] + '...' if len(name) > 20 else name 
                            for name in repo_summary['repository_name']], 
                           rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Cross-Repository User Activity (top right)
        ax2 = fig.add_subplot(gs[0, 2])
        if focus_user:
            user_repos = combined_users[combined_users['name'].str.contains(focus_user, case=False, na=False)]
            if not user_repos.empty:
                repos = user_repos['repository_name']
                contributions = user_repos['total_changes']
                
                ax2.pie(contributions, labels=repos, autopct='%1.1f%%', startangle=90)
                ax2.set_title(f'🎯 {focus_user}\nActivity Distribution', fontsize=12, fontweight='bold')
        else:
            # Show top contributors across all repos
            top_cross_repo = combined_users.groupby('name').agg({
                'total_changes': 'sum',
                'commits': 'sum'
            }).reset_index().sort_values('total_changes', ascending=False).head(8)
            
            ax2.barh(range(len(top_cross_repo)), top_cross_repo['total_changes'], 
                    color='#f39c12', alpha=0.8)
            ax2.set_yticks(range(len(top_cross_repo)))
            ax2.set_yticklabels([str(name)[:15] + '...' if len(str(name)) > 15 else str(name) 
                               for name in top_cross_repo['name']])
            ax2.set_xlabel('Total Changes')
            ax2.set_title('🏆 Top Contributors\nAcross All Repos', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3)
        
        # 3. Timeline Comparison (middle row, spans all columns)
        ax3 = fig.add_subplot(gs[1, :])
        if 'date' in combined_daily.columns:
            for i, repo in enumerate(repo_names):
                repo_data = combined_daily[combined_daily['repository_name'] == repo]
                if not repo_data.empty:
                    dates = pd.to_datetime(repo_data['date'])
                    color = plt.cm.Set1(i % 9)  # Cycle through colors
                    ax3.plot(dates, repo_data['additions'], marker='o', 
                            label=f'{repo}', linewidth=2, color=color)
        
        ax3.set_title('📈 Timeline Comparison Across Repositories', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Daily Additions')
        ax3.set_xlabel('Date')
        ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax3.grid(True, alpha=0.3)
        
        # Format dates
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        
        # 4. Repository Activity Heatmap (bottom left)
        ax4 = fig.add_subplot(gs[2, :2])
        repo_daily_summary = combined_daily.groupby(['repository_name', 'date']).agg({
            'commits': 'sum'
        }).reset_index()
        
        if not repo_daily_summary.empty:
            pivot_data = repo_daily_summary.pivot(index='repository_name', columns='date', values='commits').fillna(0)
            
            # Limit columns if too many dates
            if len(pivot_data.columns) > 15:
                pivot_data = pivot_data.iloc[:, -15:]  # Last 15 days
            
            if HAS_SEABORN:
                sns.heatmap(pivot_data, ax=ax4, cmap='YlOrRd', cbar_kws={'label': 'Commits'})
            else:
                im = ax4.imshow(pivot_data.values, cmap='YlOrRd', aspect='auto')
                ax4.set_xticks(range(len(pivot_data.columns)))
                ax4.set_yticks(range(len(pivot_data.index)))
                ax4.set_xticklabels([str(col)[-5:] for col in pivot_data.columns])  # Show last 5 chars of date
                ax4.set_yticklabels([name[:15] + '...' if len(name) > 15 else name 
                                   for name in pivot_data.index])
                plt.colorbar(im, ax=ax4, label='Commits')
            
            ax4.set_title('🔥 Cross-Repository Activity Heatmap', fontsize=12, fontweight='bold')
            ax4.set_xlabel('Date')
            ax4.set_ylabel('Repository')
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
        
        # 5. Summary Statistics (bottom right)
        ax5 = fig.add_subplot(gs[2, 2])
        total_repos = len(repo_names)
        total_additions = combined_daily['additions'].sum()
        total_deletions = combined_daily['deletions'].sum()
        total_commits = combined_daily['commits'].sum()
        total_contributors = len(combined_users['name'].unique())
        
        stats_data = [total_repos, total_additions, total_deletions, total_commits, total_contributors]
        stats_labels = ['Repos', 'Additions', 'Deletions', 'Commits', 'Contributors']
        colors = ['#9b59b6', '#2ecc71', '#e74c3c', '#3498db', '#1abc9c']
        
        bars = ax5.bar(stats_labels, stats_data, color=colors, alpha=0.8)
        ax5.set_title('📊 Overall Statistics', fontsize=12, fontweight='bold')
        ax5.set_ylabel('Count')
        
        # Add value labels
        for bar, value in zip(bars, stats_data):
            ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(stats_data)*0.01,
                    f'{value:,}', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save combined dashboard
        filename = f"{self.output_dir}/combined_multi_repo_dashboard.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"🔗 Combined dashboard saved: {filename}")
    
    def _generate_analysis_report(self, results: Dict, focus_user: Optional[str] = None):
        """Generate comprehensive markdown report"""
        
        report_filename = f"{self.output_dir}/analysis_report.md"
        
        with open(report_filename, 'w') as f:
            f.write("# 📊 Multi-Repository Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Workspace:** {self.workspace}\n")
            f.write(f"**Repositories Analyzed:** {len(results)}\n")
            if focus_user:
                f.write(f"**Focus User:** {focus_user}\n")
            f.write("\n---\n\n")
            
            # Individual repository analysis
            f.write("## 📁 Individual Repository Analysis\n\n")
            
            for repo_slug, data in results.items():
                display_name = data['display_name']
                meta = data['analysis_meta']
                
                f.write(f"### {display_name}\n\n")
                f.write(f"**Repository Slug:** `{repo_slug}`\n\n")
                f.write(f"**Analysis Period:** {meta['start_date']} to {meta['end_date']}\n")
                f.write(f"**Grouping:** {meta['group_by']}\n\n")
                
                f.write("**Statistics:**\n")
                f.write(f"- Total Additions: {meta['total_additions']:,} lines\n")
                f.write(f"- Total Deletions: {meta['total_deletions']:,} lines\n")
                f.write(f"- Net Changes: {meta['total_additions'] - meta['total_deletions']:,} lines\n")
                f.write(f"- Total Commits: {meta['total_commits']:,}\n")
                f.write(f"- Contributors: {meta['total_contributors']}\n\n")
                
                f.write("**Generated Files:**\n")
                f.write(f"- Timeline Analysis: `{repo_slug}_timeline_analysis.png`\n")
                f.write(f"- User Contributions: `{repo_slug}_user_contributions.png`\n")
                f.write(f"- Summary Dashboard: `{repo_slug}_summary_dashboard.png`\n")
                f.write(f"- Activity Heatmap: `{repo_slug}_activity_heatmap.png`\n")
                f.write(f"- Daily Data: `{repo_slug}_daily_data.csv`\n")
                f.write(f"- User Data: `{repo_slug}_user_data.csv`\n\n")
            
            # Combined analysis section
            if len(results) > 1:
                f.write("## 🔗 Combined Analysis\n\n")
                f.write("**Multi-Repository Files:**\n")
                f.write("- Combined Dashboard: `combined_multi_repo_dashboard.png`\n")
                f.write("- Combined Daily Data: `combined_daily_analysis.csv`\n")
                f.write("- Combined User Data: `combined_user_analysis.csv`\n\n")
            
            f.write("---\n\n")
            f.write("*Report generated by Multi-Repository Bitbucket LOC Analyzer*\n")
        
        logger.info(f"📝 Analysis report saved: {report_filename}")


def main():
    """Example usage of the multi-repository analyzer"""
    
    # Example configuration
    TOKEN = "your_token_here"
    BASE_URL = "https://stash.arubanetworks.com"
    WORKSPACE = "GVT"
    
    # Repository configurations with display names
    REPO_CONFIGS = [
        {
            'slug': 'cx-switch-health-read-assist',
            'display_name': 'CX Switch Health Read Assist'
        },
        {
            'slug': 'cx-switch-device-health', 
            'display_name': 'CX Switch Device Health'
        }
    ]
    
    START_DATE = "2025-06-20"
    END_DATE = "2025-06-26"
    FOCUS_USER = "manjunath.kallatti@hpe.com"  # Optional
    
    # Create analyzer
    analyzer = MultiRepoAnalyzer(TOKEN, BASE_URL, WORKSPACE)
    
    # Analyze repositories
    results = analyzer.analyze_repositories(
        REPO_CONFIGS,
        START_DATE, 
        END_DATE, 
        group_by='day',
        focus_user=FOCUS_USER
    )
    
    print(f"\n🎉 Analysis complete! Results for {len(results)} repositories:")
    for repo_slug, data in results.items():
        display_name = data['display_name']
        meta = data['analysis_meta']
        print(f"  📁 {display_name}: {meta['total_contributors']} contributors, "
              f"{meta['total_commits']} commits, {meta['total_additions']:,} additions")

if __name__ == "__main__":
    main()
