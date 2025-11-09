# Churn Prediction System - Startup Script (PowerShell)
# This script starts all required services for Windows

Write-Host "🚀 Starting Churn Prediction System..." -ForegroundColor Yellow
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# Step 1: Start Docker services
Write-Host "📦 Step 1: Starting Docker services..." -ForegroundColor Yellow
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    docker-compose up -d
    Write-Host "✅ Docker services started" -ForegroundColor Green
    Write-Host "   Waiting 10 seconds for services to initialize..."
    Start-Sleep -Seconds 10
} else {
    Write-Host "⚠️  docker-compose not found. Please start Kafka, Redis, and Zookeeper manually." -ForegroundColor Yellow
}

# Step 2: Check virtual environment
if (-not $env:VIRTUAL_ENV) {
    Write-Host "📦 Step 2: Activating virtual environment..." -ForegroundColor Yellow
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
        Write-Host "✅ Virtual environment activated" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Virtual environment not found. Please create one: python -m venv venv" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Virtual environment already activated" -ForegroundColor Green
}

# Step 3: Run migrations
Write-Host "📦 Step 3: Running database migrations..." -ForegroundColor Yellow
python manage.py migrate
Write-Host "✅ Database migrations complete" -ForegroundColor Green

# Step 3.5: Create superuser if needed
Write-Host "📦 Step 3.5: Checking for superuser..." -ForegroundColor Yellow
python scripts/create_superuser.py

# Create logs directory
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Step 4: Start Django server
Write-Host "📦 Step 4: Starting Django server..." -ForegroundColor Yellow
Start-Process python -ArgumentList "manage.py", "runserver" -WindowStyle Hidden -RedirectStandardOutput "logs\django.log" -RedirectStandardError "logs\django_error.log"
Write-Host "✅ Django server started" -ForegroundColor Green
Write-Host "   Access at: http://localhost:8000"
Write-Host "   Dashboard: http://localhost:8000/analytics/churn-dashboard/"

# Step 5: Start FastAPI collector
Write-Host "📦 Step 5: Starting FastAPI event collector..." -ForegroundColor Yellow
Set-Location "streaming\collectors"
Start-Process python -ArgumentList "-m", "uvicorn", "fastapi_collector:app", "--host", "0.0.0.0", "--port", "9000" -WindowStyle Hidden -RedirectStandardOutput "$ProjectRoot\logs\collector.log" -RedirectStandardError "$ProjectRoot\logs\collector_error.log"
Set-Location $ProjectRoot
Write-Host "✅ FastAPI collector started" -ForegroundColor Green
Write-Host "   Access at: http://localhost:9000"

# Step 6: Start Kafka consumer
Write-Host "📦 Step 6: Starting Kafka consumer..." -ForegroundColor Yellow
Start-Process python -ArgumentList "streaming\consumers\django_consumer.py" -WindowStyle Hidden -RedirectStandardOutput "logs\consumer.log" -RedirectStandardError "logs\consumer_error.log"
Write-Host "✅ Kafka consumer started" -ForegroundColor Green

# Step 7: Start Flink jobs (optional)
if ($env:START_FLINK_JOBS -ne "false") {
    Write-Host "📦 Step 7: Starting Flink processing jobs..." -ForegroundColor Yellow
    python scripts\start_flink_jobs.py
} else {
    Write-Host "📦 Step 7: Flink jobs disabled (set START_FLINK_JOBS=true to enable)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ All services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Service Status:"
Write-Host "   - Django: http://localhost:8000"
Write-Host "   - FastAPI Collector: http://localhost:9000"
Write-Host "   - Kafka Consumer: Running"
Write-Host "   - Flink Jobs: Running (if enabled)"
Write-Host "   - Flink Web UI: http://localhost:8081 (if Flink cluster is running)"
Write-Host ""
Write-Host "📝 Logs are in the logs/ directory"
Write-Host ""
Write-Host "🛑 To stop services, close the terminal or use Task Manager"

