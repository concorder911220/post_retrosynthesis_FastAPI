# PowerShell script to start services locally (without Docker)

Write-Host "Starting services locally..." -ForegroundColor Green

# Check if PostgreSQL is running (Windows)
$pgRunning = Get-Service -Name postgresql* -ErrorAction SilentlyContinue
if (-not $pgRunning) {
    Write-Host "PostgreSQL service not found. Please ensure PostgreSQL is installed and running." -ForegroundColor Yellow
}

# Initialize database
Write-Host "Initializing database..." -ForegroundColor Cyan
Set-Location $PSScriptRoot\..
python -m backend.init_db

# Start backend
Write-Host "Starting backend API on http://localhost:8000..." -ForegroundColor Cyan
Start-Process python -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $PSScriptRoot\..

# Start microservice
Write-Host "Starting microservice on http://localhost:8001..." -ForegroundColor Cyan
Start-Process python -ArgumentList "-m", "uvicorn", "microservice.main:app", "--host", "0.0.0.0", "--port", "8001" -WorkingDirectory $PSScriptRoot\..

Write-Host "Services started!" -ForegroundColor Green
Write-Host "Backend: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Microservice: http://localhost:8001" -ForegroundColor Yellow
