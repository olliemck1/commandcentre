@echo off
echo ===================================================
echo   Starting Command Centre (FastAPI + React Vite)
echo ===================================================

cd /d "%~dp0"

echo [1/2] Launching Backend on http://localhost:8000 ...
start "Command Centre Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

timeout /t 2 >nul

echo [2/2] Launching Frontend on http://localhost:5173 ...
start "Command Centre Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Application started!
echo Frontend: http://localhost:5173
echo Backend API Docs: http://localhost:8000/docs
echo.
