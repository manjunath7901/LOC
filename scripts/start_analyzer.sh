#!/bin/bash

# Enhanced Multi-Repository Bitbucket LOC Analyzer Startup Script
# This script starts the backend API server and provides instructions for frontend access

echo "🚀 Enhanced Multi-Repository Bitbucket LOC Analyzer"
echo "=========================================================="

# Check Python version
python_version=$(python3 --version 2>&1)
echo "📋 Python version: $python_version"

# Check if we're in the right directory
if [ ! -f "backend/api/app.py" ]; then
    echo "❌ Error: Please run this script from the LOC project root directory"
    echo "   Current directory: $(pwd)"
    echo "   Expected files: backend/api/app.py, frontend/index.html"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p output
echo "📁 Output directory ready: $(pwd)/output"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "✅ Dependencies installed successfully"
    else
        echo "⚠️  Some dependencies may have failed to install"
    fi
else
    echo "⚠️  requirements.txt not found, manual dependency installation may be needed"
fi

# Set up environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src:$(pwd)/backend/core"
echo "🔧 Environment configured"

# Start the backend server
echo ""
echo "🌐 Starting backend API server..."
echo "   Backend will be available at: http://localhost:5001"
echo "   API endpoints will be at: http://localhost:5001/api/"
echo ""

# Check if port 5001 is already in use
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 5001 is already in use. Stopping existing process..."
    lsof -ti:5001 | xargs kill -9 2>/dev/null
    sleep 2
fi

# Start backend in background
echo "🚀 Launching backend server..."
cd backend/api && python3 app.py &
backend_pid=$!
cd ../..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running
if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "✅ Backend server is running (PID: $backend_pid)"
else
    echo "❌ Backend server failed to start"
    exit 1
fi

# Instructions for frontend
echo ""
echo "🌐 Frontend Access Instructions:"
echo "=========================================================="
echo "1. Open your web browser"
echo "2. Navigate to: file://$(pwd)/frontend/index.html"
echo "   Or drag and drop frontend/index.html into your browser"
echo ""
echo "🔧 Alternative: Use a local web server for frontend:"
echo "   cd frontend && python3 -m http.server 8080"
echo "   Then visit: http://localhost:8080"
echo ""

# Show example usage
echo "📊 Example Multi-Repository Analysis:"
echo "=========================================================="
echo "Repository Slugs (enter in the form):"
echo "   cx-switch-health-read-assist"
echo "   cx-switch-device-health"
echo "   (each repository will get separate charts)"
echo ""
echo "Expected outputs:"
echo "   - Individual charts for each repository"
echo "   - Repository names clearly shown in chart titles"
echo "   - Combined cross-repository analysis"
echo "   - CSV files with detailed data"
echo ""

# Show monitoring information
echo "🔍 Monitoring:"
echo "=========================================================="
echo "Backend logs: Check the terminal for API request logs"
echo "Output files: Will be created in $(pwd)/output/"
echo "Backend PID: $backend_pid"
echo ""
echo "To stop the backend server:"
echo "   kill $backend_pid"
echo "   or press Ctrl+C if running in foreground"
echo ""

# Show test instructions
echo "🧪 Testing:"
echo "=========================================================="
echo "Run comprehensive tests:"
echo "   python3 tests/test_enhanced_multi_repo.py"
echo ""
echo "Test specific functionality:"
echo "   python3 tests/test_improved_analyzer.py"
echo ""

# Wait for user input to keep script running
echo "📺 System Status:"
echo "=========================================================="
echo "✅ Backend running at: http://localhost:5001"
echo "📁 Frontend available at: file://$(pwd)/frontend/index.html"
echo "📊 Output directory: $(pwd)/output/"
echo ""
echo "Press Enter to stop the backend server and exit..."
read

# Clean up
echo "🧹 Shutting down..."
kill $backend_pid 2>/dev/null
echo "✅ Backend server stopped"
echo "👋 Goodbye!"
