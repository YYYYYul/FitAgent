@echo off
chcp 65001 >nul
title FitAgent - Stop

echo ============================================
echo  FitAgent - Stop Services
echo ============================================
echo.

set "STOPPED=0"

:: --- Stop backend (port 8001) ---
echo [1/2] Checking backend (port 8001)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING" 2^>nul') do (
    set "PID=%%a"
    echo        Found process PID !PID! on port 8001. Killing...
    taskkill /F /PID !PID! >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo        Backend stopped.
        set "STOPPED=1"
    ) else (
        echo        Failed to kill PID !PID!.
    )
)
if "%STOPPED%"=="0" (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING" 2^>nul') do set "HAS8001=1"
    if not defined HAS8001 echo        No process found on port 8001.
)

:: --- Stop frontend (port 3000) ---
echo [2/2] Checking frontend (port 3000)...
set "STOPPED2=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING" 2^>nul') do (
    set "PID=%%a"
    echo        Found process PID !PID! on port 3000. Killing...
    taskkill /F /PID !PID! >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo        Frontend stopped.
        set "STOPPED2=1"
    ) else (
        echo        Failed to kill PID !PID!.
    )
)
if "%STOPPED2%"=="0" (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING" 2^>nul') do set "HAS3000=1"
    if not defined HAS3000 echo        No process found on port 3000.
)

echo.
echo ============================================
echo  Done.
echo ============================================
pause
