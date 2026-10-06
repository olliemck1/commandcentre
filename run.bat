@echo off
echo ===================================================
echo   Starting Command Centre (FastAPI + React Vite)
echo ===================================================

cd /d "%~dp0"

echo [1/3] Launching Backend on http://localhost:8000 ...
start "Command Centre Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

timeout /t 2 >nul

echo [2/3] Launching Frontend on http://localhost:5173 ...
start "Command Centre Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 1 >nul

echo [3/3] Launching Telegram Bot Service (Long Polling) ...
start "Command Centre Telegram Bot" cmd /k "cd backend && venv\Scripts\activate && python -m app.services.telegram_bot"

echo.
echo Application started!
echo Frontend: http://localhost:5173
echo Backend API Docs: http://localhost:8000/docs
echo Telegram Bot: Running (check bot window for polling logs)
echo.
