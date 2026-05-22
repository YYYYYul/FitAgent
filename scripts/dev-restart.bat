@echo off
chcp 65001 >nul
title FitAgent - Restart

echo ============================================================
echo  FitAgent - Restart
echo ============================================================
echo.

:: --- Step 1: Stop ---
echo [1/2] Stopping services...

:: Port 8001
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING" 2^>nul') do (
    echo        Killing PID %%a on port 8001...
    taskkill /F /PID %%a >nul 2>&1
)

:: Port 3000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING" 2^>nul') do (
    echo        Killing PID %%a on port 3000...
    taskkill /F /PID %%a >nul 2>&1
)

echo        Waiting for ports to release...
timeout /t 3 /nobreak >nul

:: --- Step 2: Start ---
echo [2/2] Starting services...
echo.
call "%~dp0dev-start.bat"
