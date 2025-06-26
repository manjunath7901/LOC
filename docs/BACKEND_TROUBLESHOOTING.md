# Backend Server Troubleshooting Guide

## 🔧 Common Backend Issues and Solutions

### Issue 1: ModuleNotFoundError: No module named 'flask_cors'

**Error Message:**
```
ModuleNotFoundError: No module named 'flask_cors'
```

**Solution:**
```bash
# Install the missing dependency
pip install Flask-CORS>=3.0.0

# Or install all requirements
pip install -r requirements.txt
```

### Issue 2: Port 5000 Already in Use (macOS)

**Error Message:**
```
Address already in use
```

**Explanation:**
On macOS, port 5000 is often used by AirPlay Receiver.

**Solution:**
The backend is configured to use port 5001 instead. Make sure your frontend points to the correct port:
- Backend: `http://localhost:5001`
- Frontend API calls: `http://localhost:5001/api`

### Issue 3: Import Error for multi_repo_analyzer

**Error Message:**
```
ModuleNotFoundError: No module named 'multi_repo_analyzer'
```

**Solution:**
Make sure you're running from the correct directory and the Python path is set:
```bash
# From the LOC project root
cd backend/api
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../../src:$(pwd)/../core"
python app.py
```

### Issue 4: Backend Starts but Frontend Can't Connect

**Symptoms:**
- Backend shows "Running on http://127.0.0.1:5001"
- Frontend shows connection errors

**Solution:**
1. Check the frontend is using the correct API URL:
   ```javascript
   this.apiBaseUrl = 'http://localhost:5001/api';
   ```

2. Test the backend manually:
   ```bash
   curl http://localhost:5001/api/health
   ```

3. Check for CORS issues (should be resolved with Flask-CORS)

## ✅ Quick Backend Verification

### 1. Health Check
```bash
curl http://localhost:5001/api/health
```
Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-26T23:49:06.608776",
  "version": "2.0.0"
}
```

### 2. Repository Parsing Test
```bash
curl -X POST http://localhost:5001/api/repositories/parse \
  -H "Content-Type: application/json" \
  -d '{"repo_input": "repo1, repo2"}'
```
Expected response:
```json
{
  "count": 2,
  "repositories": [
    {
      "display_name": "Repo1",
      "slug": "repo1"
    },
    {
      "display_name": "Repo2", 
      "slug": "repo2"
    }
  ]
}
```

### 3. Connection Test (will fail without real credentials)
```bash
curl -X POST http://localhost:5001/api/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "token": "test_token",
    "base_url": "https://stash.arubanetworks.com",
    "workspace": "GVT"
  }'
```

## 🚀 Recommended Startup Process

### Option 1: Easy Startup (Recommended)
```bash
./scripts/start_analyzer.sh
```

### Option 2: Manual Startup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start backend
cd backend/api
python app.py

# 3. In another terminal, open frontend
open ../../frontend/index.html
```

### Option 3: Development Mode
```bash
# Backend with debug mode
cd backend/api
FLASK_DEBUG=1 python app.py

# Frontend with local server
cd frontend
python -m http.server 8080
# Then visit http://localhost:8080
```

## 🐛 Debug Mode

To get more detailed error information:

```bash
cd backend/api
FLASK_DEBUG=1 python app.py
```

This will:
- Show detailed error tracebacks
- Auto-reload on code changes
- Provide a debugger PIN for interactive debugging

## 📊 Monitoring Backend Logs

The backend provides detailed logging. Watch for these messages:

**Successful Startup:**
```
🚀 Starting Multi-Repository Bitbucket LOC Analyzer API Server
📊 Features:
   - Multi-repository analysis with separate charts
   - RESTful API endpoints
   ...
🌐 API Base URL: http://127.0.0.1:5001
 * Running on http://127.0.0.1:5001
```

**Successful API Calls:**
```
INFO:werkzeug:127.0.0.1 - - [date] "GET /api/health HTTP/1.1" 200 -
INFO:werkzeug:127.0.0.1 - - [date] "POST /api/repositories/parse HTTP/1.1" 200 -
```

## 🔧 Environment Setup

Make sure your environment is properly configured:

```bash
# Check Python version (3.7+ required)
python --version

# Check pip packages
pip list | grep -E "(Flask|requests|pandas|matplotlib)"

# Check project structure
ls -la backend/api/
ls -la backend/core/
ls -la frontend/
```

## 📞 Getting Help

If you're still having issues:

1. **Check the terminal output** for detailed error messages
2. **Run the test suite**: `python tests/test_enhanced_multi_repo.py`
3. **Verify your environment**: Make sure all dependencies are installed
4. **Check the project structure**: Ensure all files are in the right places
5. **Test with curl**: Verify backend endpoints manually

## 🎯 Success Indicators

You know everything is working when:

✅ Backend starts without errors
✅ Health check returns JSON response  
✅ Repository parsing works correctly
✅ Frontend loads without console errors
✅ Connection test button in frontend responds (even if it fails authentication)
✅ Form validation works in the frontend
