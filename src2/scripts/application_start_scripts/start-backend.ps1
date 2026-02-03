# Start the Python backend server
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$src2Dir = Split-Path -Parent (Split-Path -Parent $scriptDir)
$venvPath = Join-Path $src2Dir "../.venv/Scripts/Activate.ps1"

# Check if virtual environment is activated, if not activate it
if (-not $env:VIRTUAL_ENV) {
    if (Test-Path $venvPath) {
        Write-Host "Activating virtual environment..." -ForegroundColor Green
        & $venvPath
    } else {
        Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Red
        Write-Host "Please create a virtual environment first: python -m venv .venv" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Cyan
Set-Location $src2Dir

# Run the FastAPI server
python run.py
