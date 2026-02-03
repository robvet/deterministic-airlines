# Activate script for Deterministic Airlines virtual environment

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))
$venvPath = Join-Path $projectRoot ".venv"
$activatePath = Join-Path $venvPath "Scripts\Activate.ps1"

Write-Host ""
Write-Host "Activating Deterministic Airlines virtual environment..." -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $venvPath)) {
    Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run setup-environment.ps1 first to create the virtual environment." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

if (-not (Test-Path $activatePath)) {
    Write-Host "Activation script not found at $activatePath" -ForegroundColor Red
    Write-Host "The virtual environment may be corrupted. Try running setup-environment.ps1 again." -ForegroundColor Yellow
    exit 1
}

& $activatePath

Write-Host "Virtual environment activated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Environment: $venvPath" -ForegroundColor Gray
Write-Host "Python:      $(python --version 2>&1)" -ForegroundColor Gray
Write-Host ""
