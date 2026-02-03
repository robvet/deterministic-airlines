# Start both frontend and backend
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$src2Dir = Split-Path -Parent $scriptDir
$venvPath = Join-Path $src2Dir "../.venv/Scripts/Activate.ps1"

# Check if virtual environment exists
if (-not (Test-Path $venvPath)) {
    Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Red
    Write-Host "Please create a virtual environment first: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Deterministic Airlines Demo..." -ForegroundColor Cyan
Write-Host ""

# Kill any existing processes on ports 8000 and 8501
Write-Host "Stopping any existing servers..." -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

# Start backend in a new terminal window
Write-Host "Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$src2Dir'; & '$venvPath'; python run.py"

# Give backend a moment to initialize
Start-Sleep -Seconds 2

# Start frontend in a new terminal window
Write-Host "Starting frontend (Streamlit)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$src2Dir\ui'; & '$venvPath'; python -m streamlit run streamlit_app.py"

# Open browser after delay
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 4
    Start-Process "http://localhost:8501"
} | Out-Null

Write-Host ""
Write-Host "Both servers starting in separate windows..." -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000 (FastAPI)" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:8501 (Streamlit)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this launcher..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
