# Enhanced Multi-Repository Bitbucket LOC Analyzer

A comprehensive tool for analyzing lines of code (LOC) changes across multiple Bitbucket repositories with enhanced visualization, proper separation of concerns, and dedicated charts for each repository.

## 🚀 Key Features

### Enhanced Multi-Repository Support
- **Separate Charts per Repository**: Each repository gets its own dedicated charts with clear repository naming
- **Repository Display Names**: User-friendly repository names automatically formatted and displayed in all charts
- **Cross-Repository Analysis**: Combined analysis showing patterns and comparisons across all repositories
- **Batch Processing**: Analyze multiple repositories in a single run with individual and combined outputs
- **Focus User Analysis**: Track specific user contributions across multiple repositories

### Improved Architecture
- **Backend/Frontend Separation**: Clean separation between Flask API backend and modern web frontend
- **REST API**: Full REST API with endpoints for analysis, progress tracking, and file serving
- **Modern Web UI**: Responsive, user-friendly web interface with real-time updates
- **Progress Tracking**: Real-time progress updates and status monitoring for long-running analyses
- **Modular Design**: Well-organized codebase with clear separation of concerns

### Visualization Enhancements
- **Repository-Specific Charts**: Each repository gets separate timeline, contribution, and summary charts
- **Clear Repository Identification**: Repository names prominently displayed in all charts and reports
- **Interactive Web Interface**: Modern, responsive web UI for easy analysis configuration
- **Real-time Progress Updates**: Live progress tracking with detailed status messages
- **Comprehensive Dashboards**: Summary statistics, activity heatmaps, and trend analysis

## 📁 Project Structure

```
LOC/
├── backend/                    # Backend API server
│   ├── core/                   # Core analysis logic
│   │   └── multi_repo_analyzer.py
│   └── api/                    # REST API endpoints
│       └── app.py
├── frontend/                   # Web frontend
│   ├── index.html             # Main UI
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css     # Responsive styles
│   │   └── js/
│   │       └── app.js         # Frontend logic
│   └── templates/             # Additional templates
├── src/                       # Core analyzer modules
│   ├── bitbucket_loc_analyzer.py    # Original analyzer
│   └── improved_bitbucket_analyzer.py # Enhanced multi-repo analyzer
├── tests/                     # Test scripts
│   ├── test_enhanced_multi_repo.py  # Comprehensive tests
│   └── test_improved_analyzer.py    # Specific functionality tests
├── output/                    # Generated charts and data
├── docs/                      # Documentation
├── scripts/                   # Utility scripts
│   └── start_analyzer.sh      # Easy startup script
└── requirements.txt           # Python dependencies
```

## 🚀 Quick Start

### Option 1: Easy Startup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd LOC

# Run the startup script
./scripts/start_analyzer.sh
```

This script will:
- Install dependencies
- Start the backend API server
- Provide frontend access instructions
- Show example usage

### Option 2: Manual Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Backend Server**
   ```bash
   cd backend/api
   python app.py
   ```

3. **Access Frontend**
   - Open `frontend/index.html` in your browser
   - Or serve it with: `cd frontend && python -m http.server 8080`

## 💻 Usage

### Web Interface (Recommended)

1. **Open the Web Interface**
   - Navigate to `frontend/index.html` in your browser
   - The interface provides a user-friendly form for configuration

2. **Configure Analysis**
   - **Bitbucket Token**: Your personal access token or app password
   - **Base URL**: Your Bitbucket server URL (e.g., `https://stash.arubanetworks.com`)
   - **Workspace/Project**: Project key or workspace name
   - **Repository Slugs**: Enter repositories (one per line or comma-separated)
     ```
     cx-switch-health-read-assist
     cx-switch-device-health
     network-automation-tools
     ```

3. **Set Analysis Parameters**
   - **Date Range**: Start and end dates for analysis
   - **Group By**: Day, week, or month
   - **Focus User**: Optional - analyze specific user's contributions

4. **Run Analysis**
   - Click "Start Enhanced Analysis"
   - Monitor real-time progress
   - View results when complete

### Key Features in Action

#### Multi-Repository Analysis
When you provide multiple repositories:
- Each repository gets its own set of charts with the repository name clearly displayed
- Charts include timeline changes, user contributions, and summary dashboards
- A combined analysis shows cross-repository patterns and comparisons

#### Repository Naming
Repository slugs are automatically formatted for display:
- `cx-switch-health-read-assist` → "CX Switch Health Read Assist"
- `network-automation-tools` → "Network Automation Tools"

#### Generated Files
For each repository:
- `{repo}_timeline_changes.png` - Daily code changes over time
- `{repo}_user_contributions.png` - Top contributors visualization
- `{repo}_summary_dashboard.png` - Comprehensive dashboard
- `{repo}_daily_changes.csv` - Detailed daily data
- `{repo}_user_contributions.csv` - User statistics

Combined analysis:
- `combined_analysis_dashboard.png` - Cross-repository comparison
- `combined_daily_changes.csv` - All repositories data combined
- `combined_user_contributions.csv` - Unified user statistics

## 🔧 API Reference

### Backend Endpoints

- `GET /api/health` - Server health check
- `POST /api/test-connection` - Test Bitbucket connection
- `POST /api/analyze` - Start analysis job
- `GET /api/jobs/{job_id}/status` - Check job status
- `GET /api/jobs/{job_id}/results` - Get analysis results
- `GET /api/files/{filename}` - Download generated files
- `POST /api/repositories/parse` - Parse repository input

### Example API Usage

```bash
# Test connection
curl -X POST http://localhost:5000/api/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_token",
    "base_url": "https://stash.arubanetworks.com",
    "workspace": "GVT"
  }'

# Start analysis
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_token",
    "base_url": "https://stash.arubanetworks.com",
    "workspace": "GVT",
    "repo_slugs": "cx-switch-health-read-assist, cx-switch-device-health",
    "start_date": "2025-06-20",
    "end_date": "2025-06-26",
    "group_by": "day",
    "focus_user": "user@example.com"
  }'
```

## 🧪 Testing

### Comprehensive Test Suite

```bash
# Run full test suite
python tests/test_enhanced_multi_repo.py

# Test specific functionality
python tests/test_improved_analyzer.py
```

### Test Coverage
- Multi-repository chart separation
- Repository name formatting
- Backend API endpoints
- Frontend-backend integration
- File organization and structure
- Progress tracking workflow

## 📊 Chart Examples

### Individual Repository Charts
Each repository generates:

1. **Timeline Changes** - Daily additions/deletions over time
2. **User Contributions** - Top contributors with additions/deletions breakdown
3. **Summary Dashboard** - Comprehensive metrics and activity heatmap

### Combined Analysis Charts
- **Repository Comparison** - Side-by-side comparison of all repositories
- **Cross-Repository Timeline** - Timeline showing all repositories together
- **Activity Heatmap** - Repository activity patterns over time

## 🔧 Configuration

### Environment Variables
```bash
export BITBUCKET_TOKEN="your_token_here"
export BITBUCKET_BASE_URL="https://stash.arubanetworks.com"
export BITBUCKET_WORKSPACE="GVT"
```

### Custom Configuration
The system supports various customization options:
- Date ranges and grouping periods
- Focus user analysis
- Custom repository display names
- Output directory configuration

## 🛠️ Development

### Adding New Features

1. **Backend**: Add endpoints in `backend/api/app.py`
2. **Core Logic**: Extend `backend/core/multi_repo_analyzer.py`
3. **Frontend**: Update `frontend/static/js/app.js`
4. **Tests**: Add tests in `tests/` directory

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📋 Requirements

- Python 3.7+
- Flask
- Requests
- Pandas
- Matplotlib
- (Optional) Seaborn for enhanced visualizations

## 🐛 Troubleshooting

### Common Issues

1. **Backend Won't Start**
   - Check if port 5000 is available
   - Verify Python dependencies are installed
   - Check for import errors in terminal

2. **Connection Failures**
   - Verify Bitbucket token permissions
   - Check base URL format
   - Ensure workspace/project key is correct

3. **No Charts Generated**
   - Verify date range has commit activity
   - Check repository names are correct
   - Ensure sufficient permissions on repositories

### Debug Mode

Start the backend in debug mode:
```bash
cd backend/api
FLASK_DEBUG=1 python app.py
```

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Support

For issues, questions, or contributions:
- Create an issue in the repository
- Check the test suite for examples
- Review the API documentation

---

**Note**: This enhanced version ensures that when analyzing multiple repositories for the same user, each repository generates separate, clearly-labeled charts with proper repository identification. The system maintains full backward compatibility while providing a modern, scalable architecture.
