#!/bin/bash
# Start both frontend and backend

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC2_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")" 
VENV_DIR="$SRC2_DIR/../.venv"

# Detect OS: Windows uses Scripts/, Unix uses bin/
if [ -f "$VENV_DIR/Scripts/activate" ]; then
    VENV_PATH="$VENV_DIR/Scripts/activate"
else
    VENV_PATH="$VENV_DIR/bin/activate"
fi

# Check if virtual environment exists
if [ ! -f "$VENV_PATH" ]; then
    echo -e "\033[31mVirtual environment not found at $VENV_PATH\033[0m"
    echo -e "\033[33mPlease create a virtual environment first: python -m venv .venv\033[0m"
    exit 1
fi

echo -e "\033[36mStarting Deterministic Airlines Demo...\033[0m"
echo ""

# Kill any existing processes on ports 8000 and 8501
echo -e "\033[33mStopping any existing servers...\033[0m"
if command -v lsof &> /dev/null; then
    # Unix/Mac
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    lsof -ti:8501 | xargs kill -9 2>/dev/null
elif command -v netstat &> /dev/null; then
    # Windows (Git Bash) - use PowerShell to kill processes
    powershell.exe -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>/dev/null
    powershell.exe -Command "Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>/dev/null
fi
sleep 1

# Start backend in background
echo -e "\033[32mStarting FastAPI backend on http://localhost:8000 ...\033[0m"
(cd "$SRC2_DIR" && source "$VENV_PATH" && python run.py) &
BACKEND_PID=$!

# Give backend a moment to initialize
sleep 2

# Start frontend in background
echo -e "\033[32mStarting frontend (Streamlit)...\033[0m"
(cd "$SRC2_DIR/ui" && source "$VENV_PATH" && python -m streamlit run streamlit_app.py) &
FRONTEND_PID=$!

# Open browser after delay
(sleep 4 && python -m webbrowser "http://localhost:8501") &

echo ""
echo -e "\033[36mBoth servers starting...\033[0m"
echo -e "\033[33m  Backend:  http://localhost:8000 (FastAPI)\033[0m"
echo -e "\033[33m  Frontend: http://localhost:8501 (Streamlit)\033[0m"
echo ""
echo -e "\033[90mPress Ctrl+C to stop both servers...\033[0m"

# Wait for both processes and handle Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
