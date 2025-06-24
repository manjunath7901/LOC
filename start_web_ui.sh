#!/bin/bash
# This script starts the Bitbucket LOC Analyzer Web UI

# Ensure we're in the correct directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -f "activate_env.sh" ]; then
  source activate_env.sh
  echo "Virtual environment activated."
fi

# Check for Flask
if ! python3 -c "import flask" &> /dev/null; then
  echo "Flask is not installed. Installing now..."
  pip install flask
fi

# Check for other requirements
if [ -f "requirements.txt" ]; then
  echo "Checking for required packages..."
  pip install -r requirements.txt
fi

# Start the web UI
echo "Starting Bitbucket LOC Analyzer Web UI..."
echo "Access the UI at http://127.0.0.1:5000"
python3 bitbucket_loc_analyzer_ui.py

# Handle exit
echo "Web UI server stopped."
