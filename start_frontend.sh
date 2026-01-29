#!/bin/bash

echo "🚀 Starting AgentY Frontend..."

# Kill any stuck processes
pkill -f vite 2>/dev/null
pkill -f "curl.*5173" 2>/dev/null

# Navigate to frontend
cd /Users/yacinebenhamou/AgentY/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start Vite dev server
echo "⚡ Starting Vite on http://localhost:5173"
npm run dev
