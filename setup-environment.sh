#!/bin/bash
# Setup script for Deterministic Airlines project
# Creates virtual environment and installs dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo ""
echo -e "\033[36m============================================\033[0m"
echo -e "\033[36m  Deterministic Airlines - Environment Setup\033[0m"
echo -e "\033[36m============================================\033[0m"
echo ""
echo -e "\033[33mThis script will:\033[0m"
echo "  1. Navigate to the project root directory"
echo "  2. Create a Python virtual environment (.venv) if it doesn't exist"
echo "  3. Install dependencies from requirements.txt"
echo "  4. Activate the virtual environment"
echo ""
echo -e "\033[90mProject root: $PROJECT_ROOT\033[0m"
echo ""

read -p "Do you want to proceed? (Y/N) " confirmation
if [[ ! "$confirmation" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "\033[33mSetup cancelled by user.\033[0m"
    exit 0
fi

echo ""
echo -e "\033[32m[Step 1/4] Navigating to project root directory...\033[0m"
cd "$PROJECT_ROOT"
echo -e "\033[90m  Current directory: $(pwd)\033[0m"

VENV_PATH="$PROJECT_ROOT/.venv"
REQUIREMENTS_PATH="$PROJECT_ROOT/requirements.txt"

# Detect OS: Windows uses Scripts/, Unix uses bin/
if [ -d "$VENV_PATH/Scripts" ] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    ACTIVATE_PATH="$VENV_PATH/Scripts/activate"
else
    ACTIVATE_PATH="$VENV_PATH/bin/activate"
fi

echo ""
echo -e "\033[32m[Step 2/4] Checking for existing virtual environment...\033[0m"
if [ -d "$VENV_PATH" ]; then
    echo -e "\033[33m  Virtual environment already exists at $VENV_PATH\033[0m"
    echo -e "\033[33m  Skipping creation.\033[0m"
else
    echo -e "\033[36m  Virtual environment not found. Creating...\033[0m"
    python -m venv .venv
    if [ $? -eq 0 ]; then
        echo -e "\033[32m  Virtual environment created successfully!\033[0m"
    else
        echo -e "\033[31m  Failed to create virtual environment!\033[0m"
        exit 1
    fi
fi

# Re-detect activate path after venv creation
if [ -f "$VENV_PATH/Scripts/activate" ]; then
    ACTIVATE_PATH="$VENV_PATH/Scripts/activate"
else
    ACTIVATE_PATH="$VENV_PATH/bin/activate"
fi

echo ""
echo -e "\033[32m[Step 3/4] Installing dependencies from requirements.txt...\033[0m"
# Temporarily activate venv to install dependencies
if [ -f "$ACTIVATE_PATH" ]; then
    source "$ACTIVATE_PATH"
else
    echo -e "\033[31m  Activation script not found at $ACTIVATE_PATH\033[0m"
    exit 1
fi

if [ -f "$REQUIREMENTS_PATH" ]; then
    echo -e "\033[90m  Running: pip install -r requirements.txt\033[0m"
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo -e "\033[32m  Dependencies installed successfully!\033[0m"
    else
        echo -e "\033[33m  Some dependencies may have failed to install.\033[0m"
    fi
else
    echo -e "\033[31m  requirements.txt not found at $REQUIREMENTS_PATH\033[0m"
    exit 1
fi

echo ""
echo -e "\033[32m[Step 4/4] Ensuring virtual environment is activated...\033[0m"
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "\033[32m  Virtual environment is already active.\033[0m"
    echo -e "\033[90m  Environment: $VIRTUAL_ENV\033[0m"
    echo -e "\033[90m  Python: $(python --version 2>&1)\033[0m"
else
    if [ -f "$ACTIVATE_PATH" ]; then
        source "$ACTIVATE_PATH"
        echo -e "\033[32m  Virtual environment activated.\033[0m"
        echo -e "\033[90m  Python: $(python --version 2>&1)\033[0m"
    else
        echo -e "\033[31m  Activation script not found at $ACTIVATE_PATH\033[0m"
        exit 1
    fi
fi

echo ""
echo -e "\033[36m============================================\033[0m"
echo -e "\033[32m  Setup Complete!\033[0m"
echo -e "\033[36m============================================\033[0m"
echo ""
echo "Your virtual environment is ready and activated."
echo -e "\033[90mTo activate it in the future, run:\033[0m"
echo -e "\033[33m  source src2/scripts/activate_environment/activate-venv.sh\033[0m"
echo ""
