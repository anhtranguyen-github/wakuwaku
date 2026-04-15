#!/bin/bash
# scripts/start_frontend.sh

# Get directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"

# Kill any existing process on port 7100
PID=$(lsof -t -i:7100)
if [ ! -z "$PID" ]; then
    echo "Killing existing frontend on port 7100 (PID: $PID)..."
    kill -9 $PID
fi

echo "Starting KanjiSchool Frontend on port 7100..."
cd $PROJECT_ROOT
# Run in background with nohup
nohup python3 scripts/frontend_server.py > $PROJECT_ROOT/frontend.log 2>&1 &

echo "Frontend started. Check $PROJECT_ROOT/frontend.log for logs."
