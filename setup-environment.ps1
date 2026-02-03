# Setup script for Deterministic Airlines project
# Creates virtual environment and installs dependencies

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Deterministic Airlines - Environment Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "  1. Navigate to the project root directory" -ForegroundColor White
Write-Host "  2. Create a Python virtual environment (.venv) if it doesn't exist" -ForegroundColor White
Write-Host "  3. Install dependencies from requirements.txt" -ForegroundColor White
Write-Host "  4. Activate the virtual environment" -ForegroundColor White
Write-Host ""
Write-Host "Project root: $projectRoot" -ForegroundColor Gray
Write-Host ""

$confirmation = Read-Host "Do you want to proceed? (Y/N)"
if ($confirmation -notmatch '^[Yy]$') {
    Write-Host ""
    Write-Host "Setup cancelled by user." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "[Step 1/4] Navigating to project root directory..." -ForegroundColor Green
Set-Location $projectRoot
Write-Host "  Current directory: $(Get-Location)" -ForegroundColor Gray

$venvPath = Join-Path $projectRoot ".venv"
$requirementsPath = Join-Path $projectRoot "requirements.txt"
$activatePath = Join-Path $venvPath "Scripts\Activate.ps1"

Write-Host ""
Write-Host "[Step 2/4] Checking for existing virtual environment..." -ForegroundColor Green
if (Test-Path $venvPath) {
    Write-Host "  Virtual environment already exists at $venvPath" -ForegroundColor Yellow
    Write-Host "  Skipping creation." -ForegroundColor Yellow
} else {
    Write-Host "  Virtual environment not found. Creating..." -ForegroundColor Cyan
    python -m venv .venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Virtual environment created successfully!" -ForegroundColor Green
    } else {
        Write-Host "  Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[Step 3/4] Installing dependencies from requirements.txt..." -ForegroundColor Green
# Temporarily activate venv to install dependencies
if (Test-Path $activatePath) {
    & $activatePath
} else {
    Write-Host "  Activation script not found at $activatePath" -ForegroundColor Red
    exit 1
}
if (Test-Path $requirementsPath) {
    Write-Host "  Running: pip install -r requirements.txt" -ForegroundColor Gray
    pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Dependencies installed successfully!" -ForegroundColor Green
    } else {
        Write-Host "  Some dependencies may have failed to install." -ForegroundColor Yellow
    }
} else {
    Write-Host "  requirements.txt not found at $requirementsPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[Step 4/4] Ensuring virtual environment is activated..." -ForegroundColor Green
if ($env:VIRTUAL_ENV) {
    Write-Host "  Virtual environment is already active." -ForegroundColor Green
    Write-Host "  Environment: $env:VIRTUAL_ENV" -ForegroundColor Gray
    Write-Host "  Python: $(python --version 2>&1)" -ForegroundColor Gray
} else {
    if (Test-Path $activatePath) {
        & $activatePath
        Write-Host "  Virtual environment activated." -ForegroundColor Green
        Write-Host "  Python: $(python --version 2>&1)" -ForegroundColor Gray
    } else {
        Write-Host "  Activation script not found at $activatePath" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your virtual environment is ready and activated." -ForegroundColor White
Write-Host "To activate it in the future, run:" -ForegroundColor Gray
Write-Host "  .\src2\scripts\activate_environment\activate-venv.ps1" -ForegroundColor Yellow
Write-Host ""
