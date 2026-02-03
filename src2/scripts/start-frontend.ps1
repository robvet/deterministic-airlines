# Start the Streamlit frontend
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$src2Dir = Split-Path -Parent $scriptDir
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

Write-Host "Starting Streamlit frontend..." -ForegroundColor Cyan
Set-Location (Join-Path $src2Dir "ui")

# Open browser after delay (give Streamlit time to start)
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:8501"
} | Out-Null

python -m streamlit run streamlit_app.py
