#!/bin/bash
# Start the Python backend server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC2_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")" 
VENV_DIR="$SRC2_DIR/../.venv"

# Detect OS: Windows uses Scripts/, Unix uses bin/
if [ -f "$VENV_DIR/Scripts/activate" ]; then
    VENV_PATH="$VENV_DIR/Scripts/activate"
else
    VENV_PATH="$VENV_DIR/bin/activate"
fi

# Check if virtual environment is activated, if not activate it
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$VENV_PATH" ]; then
        echo -e "\033[32mActivating virtual environment...\033[0m"
        source "$VENV_PATH"
    else
        echo -e "\033[31mVirtual environment not found at $VENV_PATH\033[0m"
        echo -e "\033[33mPlease create a virtual environment first: python -m venv .venv\033[0m"
        exit 1
    fi
fi

echo -e "\033[36mStarting FastAPI backend on http://localhost:8000 ...\033[0m"
cd "$SRC2_DIR"

# Kill any existing process on port 8000
echo -e "\033[33mStopping any existing backend server...\033[0m"
if command -v lsof &> /dev/null; then
    # Unix/Mac
    lsof -ti:8000 | xargs kill -9 2>/dev/null
elif command -v netstat &> /dev/null; then
    # Windows (Git Bash) - use PowerShell to kill processes
    powershell.exe -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>/dev/null
fi
sleep 1

# Run the FastAPI server
python run.py
