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

# Start Telegram Bot daemon if configured
if [ -f backend/.env ] && grep -q "TELEGRAM_BOT_TOKEN=" backend/.env; then
    (cd backend && source venv/bin/activate && python -m app.services.telegram_bot) &
    BOT_PID=$!
    trap "kill $BACKEND_PID $FRONTEND_PID $BOT_PID 2>/dev/null" EXIT
else
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
fi

wait

