# 🚀 Improved Bitbucket LOC Analyzer

An advanced, well-structured tool for analyzing Bitbucket repository contributions with enhanced multi-repository support, improved visualizations, and better project organization.

## 🎯 Key Improvements

### ✨ New Features
- **Multi-Repository Analysis**: Analyze multiple repositories simultaneously with separate charts for each
- **Enhanced Visualizations**: Comprehensive dashboards, timeline charts, and contribution analysis
- **Improved Project Structure**: Organized codebase with proper separation of concerns
- **Real-time Progress Tracking**: Live updates during analysis with detailed progress information
- **Cross-Repository Comparison**: Combined analysis showing relationships between repositories
- **Repository-Specific Charts**: Each repository gets its own set of detailed visualizations

### 📊 Chart Types
- **Timeline Charts**: Daily, weekly, or monthly code changes with cumulative trends
- **User Contribution Charts**: Horizontal bar charts and pie charts showing contributor activity
- **Summary Dashboards**: 4-panel dashboards with metrics, heatmaps, and trends
- **Combined Analysis**: Cross-repository comparison and activity correlation

## 📁 Project Structure

```
📦 Bitbucket LOC Analyzer
├── 📂 src/                          # Source code
│   ├── bitbucket_loc_analyzer.py    # Original analyzer (enhanced)
│   ├── improved_bitbucket_analyzer.py # New multi-repo analyzer
│   ├── improved_ui.py               # Enhanced web interface
│   ├── member_contributions.py      # Member analysis tools
│   └── github_loc_analyzer.py       # GitHub support
├── 📂 templates/                    # Web UI templates
│   ├── improved_index.html          # Enhanced form interface
│   └── improved_results.html        # Advanced results display
├── 📂 tests/                        # Test files and debug scripts
│   ├── test_improved_analyzer.py    # Main test suite
│   ├── test_*.py                    # Various test scripts
│   └── debug_*.py                   # Debug utilities
├── 📂 scripts/                      # Shell scripts and automation
│   ├── analyze_*.sh                 # Analysis scripts
│   └── *.sh                         # Utility scripts
├── 📂 output/                       # Generated analysis results
│   ├── *_timeline_changes.png       # Timeline charts
│   ├── *_user_contributions.png     # User charts
│   ├── *_summary_dashboard.png      # Summary dashboards
│   ├── combined_analysis_dashboard.png # Cross-repo analysis
│   ├── *.csv                        # Data files
│   └── *_summary.md                 # Analysis reports
├── 📂 docs/                         # Documentation
│   ├── *.md                         # Various documentation files
│   └── guides/                      # User guides
├── 📄 requirements.txt              # Python dependencies
└── 📄 README.md                     # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd LOC

# Install dependencies
pip install -r requirements.txt

# Create required directories (if not exists)
mkdir -p output tests src templates docs scripts
```

### 2. Running the Enhanced Web Interface

```bash
# Start the improved web UI
cd src
python improved_ui.py
```

Then open your browser to `http://127.0.0.1:5000`

### 3. Command Line Usage

```bash
# Single repository analysis
python src/bitbucket_loc_analyzer.py WORKSPACE REPO_SLUG --token YOUR_TOKEN

# Multiple repository analysis (new feature)
python src/improved_bitbucket_analyzer.py
```

## 🎨 Multi-Repository Features

### Separate Repository Analysis
Each repository gets its own comprehensive analysis:

- **📈 Timeline Chart**: `{repo}_timeline_changes.png`
  - Daily additions and deletions
  - Cumulative change trends
  - Date-range specific analysis

- **👥 User Contributions**: `{repo}_user_contributions.png`
  - Top contributors bar chart
  - Contribution distribution pie chart
  - User activity breakdown

- **📋 Summary Dashboard**: `{repo}_summary_dashboard.png`
  - Key metrics overview
  - Activity heatmap
  - Top contributors
  - Trend analysis

### Combined Cross-Repository Analysis
When analyzing multiple repositories:

- **🔗 Combined Dashboard**: `combined_analysis_dashboard.png`
  - Repository comparison
  - Cross-repo user activity
  - Timeline comparison
  - Activity correlation heatmap

- **📊 Unified Data Files**:
  - `combined_daily_changes.csv`
  - `combined_user_contributions.csv`

## 📝 Configuration Options

### Web Interface
- **Multi-Repository Input**: Comma-separated or line-separated repository slugs
- **Date Range Selection**: Start and end date pickers
- **Grouping Options**: Day, week, or month grouping
- **User Focus**: Optional focus on specific users
- **Analysis Type**: Standard or user-focused analysis

### Advanced Options
- **File Extensions**: Filter by specific file types
- **Merge Handling**: Include/exclude merge commits
- **Export Formats**: CSV, JSON data export
- **Chart Customization**: Different visualization styles

## 🔧 Technical Improvements

### Code Organization
- **Modular Architecture**: Separated concerns into distinct modules
- **Enhanced Error Handling**: Better error messages and recovery
- **Performance Optimization**: Reduced memory usage and faster rendering
- **Type Hints**: Full type annotation for better code clarity

### DataFrame Improvements
- **Fixed Ambiguity Issues**: Resolved pandas DataFrame truth value errors
- **Better Empty Checking**: Use `.empty` instead of `len() == 0`
- **Consistent Patterns**: Standardized DataFrame operations across codebase

### Visualization Enhancements
- **Repository Identification**: Clear repo names in all charts
- **Color Coding**: Consistent color schemes across visualizations
- **Responsive Design**: Charts that work on different screen sizes
- **Interactive Elements**: Clickable charts and downloadable results

## 📊 Output Files Explained

### Repository-Specific Files
```
{repository_name}_timeline_changes.png     # Timeline visualization
{repository_name}_user_contributions.png   # User analysis charts
{repository_name}_summary_dashboard.png    # Comprehensive dashboard
{repository_name}_daily_changes.csv        # Raw daily data
{repository_name}_user_contributions.csv   # User statistics
```

### Combined Analysis Files
```
combined_analysis_dashboard.png            # Cross-repo comparison
combined_daily_changes.csv                 # All repo daily data
combined_user_contributions.csv            # All repo user data
analysis_{id}_summary.md                   # Comprehensive report
```

## 🧪 Testing

### Run Tests
```bash
# Test the improved analyzer
python tests/test_improved_analyzer.py

# Test specific functionality
python tests/test_*.py
```

### Debug Mode
```bash
# Run with debugging enabled
DEBUG=1 python src/improved_ui.py
```

## 📈 Performance Improvements

- **Concurrent Processing**: Parallel repository analysis
- **Memory Optimization**: Efficient DataFrame operations
- **Caching**: Smart caching of API responses
- **Progressive Loading**: Real-time progress updates
- **Optimized Charts**: Faster chart generation and rendering

## 🛠️ Dependencies

### Core Requirements
```
pandas>=1.3.0
matplotlib>=3.5.0
requests>=2.25.0
flask>=2.0.0
```

### Optional Dependencies
```
seaborn>=0.11.0  # Enhanced visualizations
plotly>=5.0.0    # Interactive charts
```

## 🎯 Use Cases

### Development Teams
- **Sprint Analysis**: Track team productivity over sprint periods
- **Code Review Insights**: Identify active contributors and review patterns
- **Project Health**: Monitor repository activity and engagement

### Project Managers
- **Resource Planning**: Understand developer allocation across projects
- **Timeline Tracking**: Visualize project progress and milestones
- **Cross-Project Analysis**: Compare activity between different repositories

### Individual Developers
- **Personal Analytics**: Track your own contribution patterns
- **Team Comparison**: See how your contributions compare to teammates
- **Activity Trends**: Understand your coding patterns over time

## 🔐 Security Notes

- **Token Security**: Tokens are handled securely and not logged
- **Local Processing**: All analysis happens locally
- **No Data Persistence**: Tokens and sensitive data are not stored

## 🤝 Contributing

1. **Fork the Repository**
2. **Create Feature Branch**: `git checkout -b feature/amazing-feature`
3. **Follow Project Structure**: Add files to appropriate directories
4. **Add Tests**: Include tests in the `tests/` directory
5. **Update Documentation**: Update relevant documentation
6. **Submit Pull Request**

## 📋 Changelog

### v2.0.0 - Enhanced Multi-Repository Support
- ✅ Multi-repository analysis with separate charts
- ✅ Improved project structure and organization
- ✅ Enhanced web interface with better UX
- ✅ Fixed DataFrame ambiguity issues
- ✅ Added comprehensive documentation
- ✅ Real-time progress tracking
- ✅ Cross-repository comparison features

### v1.x.x - Original Features
- ✅ Single repository analysis
- ✅ Basic web interface
- ✅ CSV/JSON export
- ✅ User contribution tracking

## 📞 Support

For questions, issues, or feature requests:

1. **Check Documentation**: Review this README and docs/ folder
2. **Run Tests**: Use the test suite to verify functionality
3. **Check Issues**: Look for existing issues or create new ones
4. **Debug Mode**: Enable debugging for detailed error information

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

*Built with ❤️ for better code analysis and team insights*
