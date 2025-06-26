#!/bin/bash

# Simple Bitbucket LOC Analyzer Startup Script
# This restores the original, simple approach that users loved

echo "🚀 Starting Simple Bitbucket LOC Analyzer..."
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "simple_bitbucket_ui.py" ]; then
    echo "❌ Error: simple_bitbucket_ui.py not found. Please run this script from the LOC directory."
    exit 1
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Error: Python is not installed or not in PATH."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python -c "import flask, matplotlib, pandas" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing required packages..."
    pip install flask matplotlib pandas requests
fi

echo "✅ Dependencies checked!"
echo ""
echo "🌐 Starting web server..."
echo "   Open your browser to: http://localhost:5000"
echo "   Press Ctrl+C to stop the server"
echo ""

# Start the Flask app
python simple_bitbucket_ui.py
