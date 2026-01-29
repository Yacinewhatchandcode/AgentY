#!/bin/bash

# AgentY - Stop All Services Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛑 Stopping AgentY Multi-Agent System..."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to stop a service
stop_service() {
    local name=$1
    local pid_file=$2
    
    echo -n "Stopping $name... "
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            echo -e "${GREEN}✓ Stopped${NC}"
        else
            echo -e "${RED}✗ Not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${RED}✗ PID file not found${NC}"
    fi
}

# Stop services
if [ -d "logs" ]; then
    stop_service "MCP Gateway" "logs/mcp_gateway.pid"
    stop_service "Orchestrator" "logs/orchestrator.pid"
    stop_service "Frontend" "logs/frontend.pid"
fi

# Kill any remaining processes
echo ""
echo "Cleaning up remaining processes..."
pkill -f "python.*orchestrator.py" 2>/dev/null || true
pkill -f "python.*mcp_gateway.py" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true

echo ""
echo -e "${GREEN}✓ All services stopped${NC}"
echo ""
