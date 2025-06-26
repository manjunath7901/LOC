#!/usr/bin/env python3
"""
Improved Bitbucket LOC Analyzer with Multi-Repository Support

This version properly handles multiple repositories by creating separate charts
for each repository and providing clear repo identification in outputs.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
from typing import List, Dict, Tuple, Optional
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
from bitbucket_loc_analyzer import BitbucketLOCAnalyzer

class ImprovedBitbucketAnalyzer:
    """Enhanced analyzer with proper multi-repository support"""
    
    def __init__(self, token: str, base_url: str, workspace: str):
        self.analyzer = BitbucketLOCAnalyzer(token, base_url, workspace)
        self.output_dir = "output"
        
        # Set up plotting style
        if HAS_SEABORN:
            plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
            sns.set_palette("husl")
        else:
            plt.style.use('default')
        
    def analyze_multiple_repositories(self, 
                                    repo_slugs: List[str], 
                                    start_date: str, 
                                    end_date: str, 
                                    group_by: str = 'day',
                                    focus_user: Optional[str] = None) -> Dict:
        """
        Analyze multiple repositories and create separate charts for each
        
        Args:
            repo_slugs: List of repository slugs to analyze
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            group_by: Grouping period ('day', 'week', 'month')
            focus_user: Optional user to focus the analysis on
            
        Returns:
            Dictionary containing analysis results for each repository
        """
        results = {}
        
        print(f"🔍 Analyzing {len(repo_slugs)} repositories...")
        
        for i, repo_slug in enumerate(repo_slugs, 1):
            print(f"\n📊 [{i}/{len(repo_slugs)}] Analyzing repository: {repo_slug}")
            
            try:
                # Analyze individual repository
                daily_data, user_data = self.analyzer.analyze_repository(
                    repo_slug, start_date, end_date, group_by, focus_user
                )
                
                if daily_data.empty or user_data.empty:
                    print(f"⚠️  No data found for repository: {repo_slug}")
                    continue
                
                # Store results
                results[repo_slug] = {
                    'daily_data': daily_data,
                    'user_data': user_data,
                    'repo_slug': repo_slug
                }
                
                # Create repository-specific charts
                self._create_repository_charts(repo_slug, daily_data, user_data, focus_user)
                
                # Save repository-specific data
                self._save_repository_data(repo_slug, daily_data, user_data, focus_user)
                
                print(f"✅ Analysis complete for {repo_slug}")
                
            except Exception as e:
                print(f"❌ Error analyzing repository {repo_slug}: {str(e)}")
                continue
        
        # Create combined analysis if multiple repos
        if len(results) > 1:
            self._create_combined_analysis(results, focus_user)
        
        return results
    
    def _create_repository_charts(self, 
                                repo_slug: str, 
                                daily_data: pd.DataFrame, 
                                user_data: pd.DataFrame,
                                focus_user: Optional[str] = None):
        """Create charts specific to a single repository"""
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create timeline chart
        self._create_timeline_chart(repo_slug, daily_data, focus_user)
        
        # Create user contributions chart
        self._create_user_contributions_chart(repo_slug, user_data, focus_user)
        
        # Create summary statistics chart
        self._create_summary_chart(repo_slug, daily_data, user_data, focus_user)
    
    def _create_timeline_chart(self, 
                             repo_slug: str, 
                             daily_data: pd.DataFrame,
                             focus_user: Optional[str] = None):
        """Create timeline chart for a repository"""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Convert date column to datetime if it's not already
        if 'date' in daily_data.columns:
            daily_data['date'] = pd.to_datetime(daily_data['date'])
            daily_data = daily_data.sort_values('date')
        
        # Chart 1: Daily additions and deletions
        if not daily_data.empty:
            dates = daily_data['date']
            additions = daily_data.get('additions', [0] * len(dates))
            deletions = daily_data.get('deletions', [0] * len(dates))
            
            ax1.bar(dates, additions, alpha=0.7, color='green', label='Additions', width=0.8)
            ax1.bar(dates, [-d for d in deletions], alpha=0.7, color='red', label='Deletions', width=0.8)
            
            ax1.set_title(f'📈 Daily Code Changes - {repo_slug}' + 
                         (f' (User: {focus_user})' if focus_user else ''))
            ax1.set_ylabel('Lines of Code')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Format x-axis
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Chart 2: Cumulative changes
        if not daily_data.empty:
            cumulative_additions = daily_data['additions'].cumsum()
            cumulative_deletions = daily_data['deletions'].cumsum()
            
            ax2.plot(dates, cumulative_additions, color='green', marker='o', 
                    linewidth=2, markersize=4, label='Cumulative Additions')
            ax2.plot(dates, cumulative_deletions, color='red', marker='s', 
                    linewidth=2, markersize=4, label='Cumulative Deletions')
            
            ax2.set_title(f'📊 Cumulative Code Changes - {repo_slug}')
            ax2.set_ylabel('Cumulative Lines')
            ax2.set_xlabel('Date')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # Format x-axis
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save the chart
        filename = f"{self.output_dir}/{repo_slug}_timeline_changes.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"📊 Timeline chart saved: {filename}")
    
    def _create_user_contributions_chart(self, 
                                       repo_slug: str, 
                                       user_data: pd.DataFrame,
                                       focus_user: Optional[str] = None):
        """Create user contributions chart for a repository"""
        
        if user_data.empty:
            return
        
        # Limit to top 15 users for readability
        top_users = user_data.head(15).copy()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Chart 1: Additions vs Deletions
        users = top_users['name'] if 'name' in top_users.columns else top_users.index
        additions = top_users.get('additions', [0] * len(users))
        deletions = top_users.get('deletions', [0] * len(users))
        
        y_pos = range(len(users))
        
        ax1.barh(y_pos, additions, alpha=0.8, color='green', label='Additions')
        ax1.barh(y_pos, [-d for d in deletions], alpha=0.8, color='red', label='Deletions')
        
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels([str(u)[:20] + '...' if len(str(u)) > 20 else str(u) for u in users])
        ax1.set_xlabel('Lines of Code')
        ax1.set_title(f'👥 User Contributions - {repo_slug}' + 
                     (f'\n(Focused on: {focus_user})' if focus_user else ''))
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Chart 2: Total changes pie chart (top 10)
        if len(top_users) > 0:
            top_10 = top_users.head(10)
            total_changes = top_10.get('total_changes', top_10.get('additions', []) + top_10.get('deletions', []))
            
            # Only create pie chart if we have meaningful data
            if sum(total_changes) > 0:
                labels = [str(u)[:15] + '...' if len(str(u)) > 15 else str(u) for u in top_10['name']]
                colors = plt.cm.Set3(range(len(labels)))
                
                wedges, texts, autotexts = ax2.pie(total_changes, labels=labels, autopct='%1.1f%%',
                                                  colors=colors, startangle=90)
                ax2.set_title(f'📊 Contribution Share - {repo_slug}\n(Top 10 Contributors)')
                
                # Improve text readability
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
        
        plt.tight_layout()
        
        # Save the chart
        filename = f"{self.output_dir}/{repo_slug}_user_contributions.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"👥 User contributions chart saved: {filename}")
    
    def _create_summary_chart(self, 
                            repo_slug: str, 
                            daily_data: pd.DataFrame, 
                            user_data: pd.DataFrame,
                            focus_user: Optional[str] = None):
        """Create summary statistics chart for a repository"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Summary statistics
        total_additions = daily_data['additions'].sum() if not daily_data.empty else 0
        total_deletions = daily_data['deletions'].sum() if not daily_data.empty else 0
        total_commits = daily_data['commits'].sum() if 'commits' in daily_data.columns and not daily_data.empty else 0
        active_days = len(daily_data[daily_data['commits'] > 0]) if not daily_data.empty else 0
        unique_contributors = len(user_data) if not user_data.empty else 0
        
        # Chart 1: Summary metrics
        metrics = ['Total\nAdditions', 'Total\nDeletions', 'Total\nCommits', 'Active\nDays', 'Contributors']
        values = [total_additions, total_deletions, total_commits, active_days, unique_contributors]
        colors = ['green', 'red', 'blue', 'orange', 'purple']
        
        bars = ax1.bar(metrics, values, color=colors, alpha=0.7)
        ax1.set_title(f'📋 Repository Summary - {repo_slug}')
        ax1.set_ylabel('Count')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                    f'{value:,}', ha='center', va='bottom', fontweight='bold')
        
        # Chart 2: Daily activity heatmap (if enough data)
        if not daily_data.empty and len(daily_data) > 7:
            daily_data['weekday'] = pd.to_datetime(daily_data['date']).dt.day_name()
            daily_data['week'] = pd.to_datetime(daily_data['date']).dt.isocalendar().week
            
            # Create pivot table for heatmap
            heatmap_data = daily_data.pivot_table(
                values='commits', 
                index='weekday', 
                columns='week', 
                aggfunc='sum', 
                fill_value=0
            )
            
            # Reorder weekdays
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = heatmap_data.reindex([day for day in weekday_order if day in heatmap_data.index])
            
            if HAS_SEABORN:
                sns.heatmap(heatmap_data, ax=ax2, cmap='YlOrRd', annot=True, fmt='g', cbar_kws={'label': 'Commits'})
            else:
                im = ax2.imshow(heatmap_data.values, cmap='YlOrRd', aspect='auto')
                ax2.set_xticks(range(len(heatmap_data.columns)))
                ax2.set_yticks(range(len(heatmap_data.index)))
                ax2.set_xticklabels(heatmap_data.columns)
                ax2.set_yticklabels(heatmap_data.index)
                plt.colorbar(im, ax=ax2, label='Commits')
            ax2.set_title(f'🔥 Activity Heatmap - {repo_slug}')
            ax2.set_xlabel('Week Number')
            ax2.set_ylabel('Day of Week')
        else:
            ax2.text(0.5, 0.5, 'Insufficient data\nfor heatmap', ha='center', va='center', 
                    transform=ax2.transAxes, fontsize=14)
            ax2.set_title('🔥 Activity Heatmap - Insufficient Data')
        
        # Chart 3: Top contributors
        if not user_data.empty:
            top_5 = user_data.head(5)
            contributors = [str(name)[:15] + '...' if len(str(name)) > 15 else str(name) 
                          for name in top_5['name']]
            contributions = top_5.get('total_changes', top_5.get('additions', [0] * len(contributors)))
            
            bars = ax3.barh(contributors, contributions, color='skyblue', alpha=0.8)
            ax3.set_title(f'🏆 Top 5 Contributors - {repo_slug}')
            ax3.set_xlabel('Total Changes')
            
            # Add value labels
            for bar, value in zip(bars, contributions):
                ax3.text(bar.get_width() + max(contributions)*0.01, bar.get_y() + bar.get_height()/2,
                        f'{value:,}', ha='left', va='center', fontweight='bold')
        
        # Chart 4: Timeline trends
        if not daily_data.empty and len(daily_data) > 1:
            dates = pd.to_datetime(daily_data['date'])
            ax4.plot(dates, daily_data['additions'], color='green', marker='o', label='Additions', linewidth=2)
            ax4.plot(dates, daily_data['deletions'], color='red', marker='s', label='Deletions', linewidth=2)
            
            ax4.set_title(f'📈 Trend Analysis - {repo_slug}')
            ax4.set_ylabel('Lines of Code')
            ax4.set_xlabel('Date')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            # Format x-axis
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save the chart
        filename = f"{self.output_dir}/{repo_slug}_summary_dashboard.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"📋 Summary dashboard saved: {filename}")
    
    def _save_repository_data(self, 
                            repo_slug: str, 
                            daily_data: pd.DataFrame, 
                            user_data: pd.DataFrame,
                            focus_user: Optional[str] = None):
        """Save repository-specific data files"""
        
        # Add repository name to data
        daily_data_copy = daily_data.copy()
        user_data_copy = user_data.copy()
        
        daily_data_copy['repository'] = repo_slug
        user_data_copy['repository'] = repo_slug
        
        # Save CSV files
        daily_filename = f"{self.output_dir}/{repo_slug}_daily_changes.csv"
        user_filename = f"{self.output_dir}/{repo_slug}_user_contributions.csv"
        
        daily_data_copy.to_csv(daily_filename, index=False)
        user_data_copy.to_csv(user_filename, index=False)
        
        print(f"💾 Data saved: {daily_filename}, {user_filename}")
    
    def _create_combined_analysis(self, results: Dict, focus_user: Optional[str] = None):
        """Create combined analysis across all repositories"""
        
        print("\n🔗 Creating combined analysis across repositories...")
        
        # Combine all data
        all_daily_data = []
        all_user_data = []
        
        for repo_slug, data in results.items():
            daily_data = data['daily_data'].copy()
            user_data = data['user_data'].copy()
            
            daily_data['repository'] = repo_slug
            user_data['repository'] = repo_slug
            
            all_daily_data.append(daily_data)
            all_user_data.append(user_data)
        
        if all_daily_data and all_user_data:
            combined_daily = pd.concat(all_daily_data, ignore_index=True)
            combined_users = pd.concat(all_user_data, ignore_index=True)
            
            # Create combined charts
            self._create_combined_charts(combined_daily, combined_users, list(results.keys()), focus_user)
            
            # Save combined data
            combined_daily.to_csv(f"{self.output_dir}/combined_daily_changes.csv", index=False)
            combined_users.to_csv(f"{self.output_dir}/combined_user_contributions.csv", index=False)
            
            print("✅ Combined analysis complete!")
    
    def _create_combined_charts(self, 
                              combined_daily: pd.DataFrame, 
                              combined_users: pd.DataFrame, 
                              repo_names: List[str],
                              focus_user: Optional[str] = None):
        """Create charts showing data across all repositories"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
        
        # Chart 1: Repository comparison
        repo_summary = combined_daily.groupby('repository').agg({
            'additions': 'sum',
            'deletions': 'sum',
            'commits': 'sum'
        }).reset_index()
        
        x = range(len(repo_summary))
        width = 0.25
        
        ax1.bar([i - width for i in x], repo_summary['additions'], width, 
               label='Additions', color='green', alpha=0.8)
        ax1.bar(x, repo_summary['deletions'], width, 
               label='Deletions', color='red', alpha=0.8)
        ax1.bar([i + width for i in x], repo_summary['commits'], width, 
               label='Commits', color='blue', alpha=0.8)
        
        ax1.set_xlabel('Repository')
        ax1.set_ylabel('Count')
        ax1.set_title('📊 Repository Comparison' + (f' (User: {focus_user})' if focus_user else ''))
        ax1.set_xticks(x)
        ax1.set_xticklabels([name[:15] + '...' if len(name) > 15 else name for name in repo_summary['repository']], 
                           rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Chart 2: Cross-repository user activity
        if focus_user:
            user_repos = combined_users[combined_users['name'].str.contains(focus_user, case=False, na=False)]
            if not user_repos.empty:
                repos = user_repos['repository']
                contributions = user_repos['total_changes']
                
                ax2.pie(contributions, labels=repos, autopct='%1.1f%%', startangle=90)
                ax2.set_title(f'🎯 {focus_user} Activity Distribution')
        else:
            # Show top contributors across all repos
            top_cross_repo = combined_users.groupby('name').agg({
                'total_changes': 'sum',
                'commits': 'sum'
            }).reset_index().sort_values('total_changes', ascending=False).head(10)
            
            ax2.barh(range(len(top_cross_repo)), top_cross_repo['total_changes'], color='orange', alpha=0.8)
            ax2.set_yticks(range(len(top_cross_repo)))
            ax2.set_yticklabels([str(name)[:20] + '...' if len(str(name)) > 20 else str(name) 
                               for name in top_cross_repo['name']])
            ax2.set_xlabel('Total Changes')
            ax2.set_title('🏆 Top Contributors Across All Repositories')
            ax2.grid(True, alpha=0.3)
        
        # Chart 3: Timeline across repositories
        if 'date' in combined_daily.columns:
            for repo in repo_names:
                repo_data = combined_daily[combined_daily['repository'] == repo]
                if not repo_data.empty:
                    dates = pd.to_datetime(repo_data['date'])
                    ax3.plot(dates, repo_data['additions'], marker='o', label=f'{repo} (Additions)', linewidth=2)
        
        ax3.set_title('📈 Timeline Comparison Across Repositories')
        ax3.set_ylabel('Additions')
        ax3.set_xlabel('Date')
        ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax3.grid(True, alpha=0.3)
        
        # Chart 4: Repository activity heatmap
        repo_daily_summary = combined_daily.groupby(['repository', 'date']).agg({
            'commits': 'sum'
        }).reset_index()
        
        if not repo_daily_summary.empty:
            pivot_data = repo_daily_summary.pivot(index='repository', columns='date', values='commits').fillna(0)
            
            # Limit columns if too many dates
            if len(pivot_data.columns) > 20:
                pivot_data = pivot_data.iloc[:, -20:]  # Last 20 days
            
            if HAS_SEABORN:
                sns.heatmap(pivot_data, ax=ax4, cmap='YlOrRd', cbar_kws={'label': 'Commits'})
            else:
                im = ax4.imshow(pivot_data.values, cmap='YlOrRd', aspect='auto')
                ax4.set_xticks(range(len(pivot_data.columns)))
                ax4.set_yticks(range(len(pivot_data.index)))
                ax4.set_xticklabels(pivot_data.columns)
                ax4.set_yticklabels(pivot_data.index)
                plt.colorbar(im, ax=ax4, label='Commits')
            ax4.set_title('🔥 Repository Activity Heatmap')
            ax4.set_xlabel('Date')
            ax4.set_ylabel('Repository')
            
            # Rotate x-axis labels for better readability
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save combined chart
        filename = f"{self.output_dir}/combined_analysis_dashboard.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"🔗 Combined analysis chart saved: {filename}")

def main():
    """Example usage of the improved analyzer"""
    
    # Example configuration - replace with actual values
    TOKEN = "your_token_here"
    BASE_URL = "https://stash.arubanetworks.com"
    WORKSPACE = "GVT"
    
    # Multiple repositories to analyze
    REPOSITORIES = [
        "cx-switch-health-read-assist",
        "cx-switch-device-health"
    ]
    
    START_DATE = "2025-06-20"
    END_DATE = "2025-06-26"
    FOCUS_USER = "manjunath.kallatti@hpe.com"  # Optional
    
    # Create analyzer
    analyzer = ImprovedBitbucketAnalyzer(TOKEN, BASE_URL, WORKSPACE)
    
    # Analyze repositories
    results = analyzer.analyze_multiple_repositories(
        REPOSITORIES, 
        START_DATE, 
        END_DATE, 
        group_by='day',
        focus_user=FOCUS_USER
    )
    
    print(f"\n🎉 Analysis complete! Results for {len(results)} repositories:")
    for repo, data in results.items():
        print(f"  📁 {repo}: {len(data['user_data'])} contributors, {len(data['daily_data'])} days of activity")

if __name__ == "__main__":
    main()
