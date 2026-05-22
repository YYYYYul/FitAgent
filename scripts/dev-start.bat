@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title FitAgent - Startup

:: ============================================================
::  1. Locate project root (relative to this script)
:: ============================================================
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"
echo ============================================================
echo  FitAgent Dev Startup
echo  Project: %CD%
echo ============================================================
echo.

:: ============================================================
::  2. Check Conda
:: ============================================================
echo [1/8] Checking Conda...
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] conda not found on PATH.
    echo         Install Anaconda or Miniconda first:
    echo         https://docs.conda.io/en/latest/miniconda.html
    echo         Make sure "Add to PATH" is checked during install.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('conda --version 2^>nul') do set "CONDA_VER=%%i"
echo        Conda: !CONDA_VER!

:: ============================================================
::  3. Check / Create fitagent conda environment
:: ============================================================
echo [2/8] Checking conda environment 'fitagent'...

:: Use conda run to check if env exists (more reliable in bat)
set "ENV_EXISTS=0"
conda info --envs 2>nul | findstr /C:"fitagent" >nul 2>&1
if %ERRORLEVEL% EQU 0 set "ENV_EXISTS=1"

if "!ENV_EXISTS!"=="0" (
    echo        Environment 'fitagent' not found. Creating from environment.yml...
    echo        This may take a few minutes...
    conda env create -f environment.yml
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to create conda environment.
        echo         Check the error output above.
        echo         You can also create manually:
        echo           conda env create -f environment.yml
        pause
        exit /b 1
    )
    echo        Environment 'fitagent' created.
) else (
    echo        Environment 'fitagent' already exists.
)

:: ============================================================
::  4. Check backend/.env
:: ============================================================
echo [3/8] Checking backend/.env...
if not exist "backend\.env" (
    echo [WARN]  backend\.env not found.
    echo         The system can start but may not work correctly.
    echo         Create one with at minimum:
    echo           DATABASE_URL=sqlite+aiosqlite:///./fitagent.db
    echo.
    echo         For LLM support, add:
    echo           LLM_API_KEY=your-api-key
    echo           LLM_BASE_URL=https://api.deepseek.com/v1
    echo           LLM_MODEL=deepseek-chat
    echo.
) else (
    :: Quick check for LLM_API_KEY
    findstr /C:"LLM_API_KEY=your-api-key-here" "backend\.env" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [WARN]  LLM_API_KEY is still a placeholder. System runs in fallback mode.
    )
    findstr /C:"LLM_API_KEY=sk-" "backend\.env" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo        LLM_API_KEY configured. LLM mode enabled.
    )
)

:: ============================================================
::  5. Install backend dependencies
:: ============================================================
echo [4/8] Installing backend dependencies...
echo        Running: conda run -n fitagent pip install -r backend/requirements.txt --quiet
conda run -n fitagent pip install -r backend/requirements.txt --quiet 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN]  pip install had warnings. Check above.
)
echo        Backend dependencies OK.

:: ============================================================
::  6. Database migration
:: ============================================================
echo [5/8] Running database migration...
conda run -n fitagent python -m alembic -c backend/alembic.ini upgrade head 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] alembic migration failed.
    echo         Try running manually:
    echo           cd backend
    echo           conda activate fitagent
    echo           alembic upgrade head
    pause
    exit /b 1
)
echo        Database up to date.

:: ============================================================
::  7. Install frontend dependencies
:: ============================================================
echo [6/8] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo        node_modules not found. Running npm install...
    cd frontend
    call npm install
    cd ..
) else (
    echo        node_modules exists, skipping npm install.
)

:: ============================================================
::  8. Stop old processes on target ports
:: ============================================================
echo [7/8] Checking for old processes...

:: Port 8001
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING" 2^>nul') do (
    echo        Found process PID %%a on port 8001. Killing...
    taskkill /F /PID %%a >nul 2>&1
)

:: Port 3000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING" 2^>nul') do (
    echo        Found process PID %%a on port 3000. Killing...
    taskkill /F /PID %%a >nul 2>&1
)

:: Wait for ports to release
timeout /t 2 /nobreak >nul

:: ============================================================
::  9. Launch services in new windows
:: ============================================================
echo [8/8] Starting services...

:: --- Backend window ---
start "FitAgent Backend" cmd /k ^
  "cd /d %CD%\backend && conda activate fitagent && python -m uvicorn app.main:app --port 8001"

:: --- Frontend window ---
start "FitAgent Frontend" cmd /k ^
  "cd /d %CD%\frontend && npm run dev"

echo.
echo ============================================================
echo  Starting services...
echo.
echo  Frontend:   http://localhost:3000
echo  Backend:    http://localhost:8001
echo  API Docs:   http://localhost:8001/docs
echo  Health:     http://localhost:8001/health
echo.
echo  Keep the backend and frontend windows open.
echo  Close them (or run dev-stop.bat) when done.
echo ============================================================
echo.
pause
