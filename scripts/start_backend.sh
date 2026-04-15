#!/bin/bash
# scripts/start_backend.sh

# Get directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"

# Kill any existing process on port 7000
PID=$(lsof -t -i:7000)
if [ ! -z "$PID" ]; then
    echo "Killing existing backend on port 7000 (PID: $PID)..."
    kill -9 $PID
fi

# Set environment
export PYTHONPATH=$PROJECT_ROOT/hanachan-fastapi/src
cd $PROJECT_ROOT/hanachan-fastapi/src

# Load .env variables if file exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

echo "Starting Hanachan Backend on port 7000..."
# Run in background with nohup
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7000 --reload > "../../backend.log" 2>&1 &

echo "Backend started. Check $PROJECT_ROOT/backend.log for logs."
