#!/bin/bash

# Churn Prediction System - Stop Script
# This script stops all running services

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🛑 Stopping Churn Prediction System..."
echo ""

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# Stop services by PID
if [ -d "logs" ]; then
    for pid_file in logs/*.pid; do
        if [ -f "$pid_file" ]; then
            PID=$(cat "$pid_file")
            SERVICE=$(basename "$pid_file" .pid)
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "${YELLOW}Stopping $SERVICE (PID: $PID)...${NC}"
                kill $PID 2>/dev/null || true
                echo -e "${GREEN}✅ $SERVICE stopped${NC}"
            else
                echo -e "${YELLOW}$SERVICE was not running${NC}"
            fi
            rm -f "$pid_file"
        fi
    done
fi

# Stop Flink jobs
echo -e "${YELLOW}Stopping Flink jobs...${NC}"
if [ -f "scripts/stop_flink_jobs.py" ]; then
    python scripts/stop_flink_jobs.py
fi

# Stop Docker services
echo -e "${YELLOW}Stopping Docker services...${NC}"
if command -v docker-compose &> /dev/null; then
    docker-compose down
    echo -e "${GREEN}✅ Docker services stopped${NC}"
else
    echo "⚠️  docker-compose not found. Please stop Docker services manually."
fi

echo ""
echo -e "${GREEN}✅ All services stopped${NC}"

