#!/bin/bash

# AgentY - Multi-Agent System Startup Script
# Starts all required services in the background

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting AgentY Multi-Agent System..."
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Ollama is running
echo -n "Checking Ollama... "
if curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}⚠ Not running${NC}"
    echo "Please start Ollama first: ollama serve"
    exit 1
fi

# Check if qwen3:8b model is available
echo -n "Checking qwen3:8b model... "
if curl -s http://127.0.0.1:11434/api/tags | grep -q "qwen3:8b"; then
    echo -e "${GREEN}✓ Available${NC}"
else
    echo -e "${YELLOW}⚠ Not found${NC}"
    echo "Pulling qwen3:8b model..."
    ollama pull qwen3:8b
fi

# Kill any existing processes
echo ""
echo "Cleaning up existing processes..."
pkill -f "python.*orchestrator.py" 2>/dev/null || true
pkill -f "python.*mcp_gateway.py" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true
sleep 2

# Create logs directory
mkdir -p logs

# Start MCP Gateway
echo -n "Starting MCP Gateway (port 8000)... "
cd backend
source .venv/bin/activate
nohup python mcp_gateway.py > ../logs/mcp_gateway.log 2>&1 &
MCP_PID=$!
sleep 2

if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running (PID: $MCP_PID)${NC}"
else
    echo -e "${YELLOW}✗ Failed to start${NC}"
    exit 1
fi

# Start Orchestrator
echo -n "Starting Orchestrator (port 8001)... "
nohup python orchestrator.py > ../logs/orchestrator.log 2>&1 &
ORCH_PID=$!
sleep 3

if curl -s http://127.0.0.1:8001/agents > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running (PID: $ORCH_PID)${NC}"
else
    echo -e "${YELLOW}✗ Failed to start${NC}"
    exit 1
fi

cd ..

# Start Frontend
echo -n "Starting Frontend (port 5173)... "
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 4

if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${YELLOW}✗ Failed to start${NC}"
    exit 1
fi

cd ..

# Save PIDs
echo "$MCP_PID" > logs/mcp_gateway.pid
echo "$ORCH_PID" > logs/orchestrator.pid
echo "$FRONTEND_PID" > logs/frontend.pid

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ AgentY is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo "  • MCP Gateway:   http://127.0.0.1:8000"
echo "  • Orchestrator:  http://127.0.0.1:8001"
echo "  • Frontend:      http://localhost:5173"
echo "  • Ollama:        http://127.0.0.1:11434"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo "  • MCP Gateway:   logs/mcp_gateway.log"
echo "  • Orchestrator:  logs/orchestrator.log"
echo "  • Frontend:      logs/frontend.log"
echo ""
echo -e "${BLUE}Open in browser:${NC}"
echo "  open http://localhost:5173"
echo ""
echo -e "${BLUE}To stop all services:${NC}"
echo "  ./stop.sh"
echo ""
