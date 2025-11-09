#!/bin/bash

# Churn Prediction System - Startup Script
# This script starts all required services

set -e

echo "🚀 Starting Churn Prediction System..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Step 1: Start Docker services (Kafka, Redis, Zookeeper)
echo -e "${YELLOW}📦 Step 1: Starting Docker services...${NC}"
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
    echo -e "${GREEN}✅ Docker services started${NC}"
    echo "   Waiting 10 seconds for services to initialize..."
    sleep 10
else
    echo "⚠️  docker-compose not found. Please start Kafka, Redis, and Zookeeper manually."
fi

# Step 2: Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}📦 Step 2: Activating virtual environment...${NC}"
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
    else
        echo "⚠️  Virtual environment not found. Please create one: python3 -m venv venv"
    fi
else
    echo -e "${GREEN}✅ Virtual environment already activated${NC}"
fi

# Step 3: Run database migrations
echo -e "${YELLOW}📦 Step 3: Running database migrations...${NC}"
python manage.py migrate
echo -e "${GREEN}✅ Database migrations complete${NC}"

# Step 3.5: Create superuser if needed
echo -e "${YELLOW}📦 Step 3.5: Checking for superuser...${NC}"
python scripts/create_superuser.py

# Step 4: Start Django server (in background)
echo -e "${YELLOW}📦 Step 4: Starting Django server...${NC}"
python manage.py runserver > logs/django.log 2>&1 &
DJANGO_PID=$!
echo -e "${GREEN}✅ Django server started (PID: $DJANGO_PID)${NC}"
echo "   Access at: http://localhost:8000"
echo "   Dashboard: http://localhost:8000/analytics/churn-dashboard/"

# Step 5: Start FastAPI collector (in background)
echo -e "${YELLOW}📦 Step 5: Starting FastAPI event collector...${NC}"
cd streaming/collectors
uvicorn fastapi_collector:app --host 0.0.0.0 --port 9000 > ../../logs/collector.log 2>&1 &
COLLECTOR_PID=$!
cd "$PROJECT_ROOT"
echo -e "${GREEN}✅ FastAPI collector started (PID: $COLLECTOR_PID)${NC}"
echo "   Access at: http://localhost:9000"
echo "   Health check: http://localhost:9000/"

# Step 6: Start Kafka consumer (in background)
echo -e "${YELLOW}📦 Step 6: Starting Kafka consumer...${NC}"
python streaming/consumers/django_consumer.py > logs/consumer.log 2>&1 &
CONSUMER_PID=$!
echo -e "${GREEN}✅ Kafka consumer started (PID: $CONSUMER_PID)${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

# Save PIDs to file for easy stopping
echo "$DJANGO_PID" > logs/django.pid
echo "$COLLECTOR_PID" > logs/collector.pid
echo "$CONSUMER_PID" > logs/consumer.pid

echo ""
echo -e "${GREEN}✅ All services started successfully!${NC}"
echo ""
echo "📊 Service Status:"
echo "   - Django: http://localhost:8000"
echo "   - FastAPI Collector: http://localhost:9000"
echo "   - Kafka Consumer: Running"
echo ""
echo "📝 Logs:"
echo "   - Django: logs/django.log"
echo "   - Collector: logs/collector.log"
echo "   - Consumer: logs/consumer.log"
echo ""
echo "🛑 To stop all services, run: ./scripts/stop_all.sh"
echo "   Or manually: kill \$(cat logs/*.pid)"

