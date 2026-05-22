@echo off
chcp 65001 >nul
title FitAgent Dev Startup

echo ============================================
echo  FitAgent — Local Dev Startup (Windows)
echo ============================================
echo.

:: Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Install Node.js 18+ and add to PATH.
    pause
    exit /b 1
)

:: Check .env
if not exist "backend\.env" (
    echo [WARN]  backend\.env not found.
    echo         Copy backend\.env.example to backend\.env or create one manually.
    echo         The system can start, but may not work correctly without config.
    echo.
)

:: Check database
if not exist "backend\fitagent.db" (
    echo [WARN]  Database not found. Running migration...
    cd backend
    python -m alembic upgrade head
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Database migration failed. Check your setup.
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo [OK]    Database created.
    echo.
)

:: Run environment check
echo Running environment check...
python scripts\check-env.py
echo.

:: Start Backend in new window
echo Starting Backend (FastAPI :8001)...
start "FitAgent Backend" cmd /k "cd /d %~dp0..\backend && python -m uvicorn app.main:app --port 8001"

:: Wait for backend to start
echo Waiting for backend to start...
timeout /t 4 /nobreak >nul

:: Start Frontend in new window
echo Starting Frontend (Next.js :3000)...
start "FitAgent Frontend" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo ============================================
echo  Both services starting in separate windows.
echo.
echo  Frontend:   http://localhost:3000
echo  Backend:    http://localhost:8001
echo  API Docs:   http://localhost:8001/docs
echo  Health:     http://localhost:8001/health
echo ============================================
echo.
echo Close this window when you are done,
echo or close the individual backend/frontend windows.
pause
