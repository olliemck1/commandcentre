#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==================================================="
echo "  Starting Command Centre (FastAPI + React Vite)   "
echo "==================================================="

# Start backend
(cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

# Start frontend
(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
