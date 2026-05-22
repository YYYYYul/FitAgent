@echo off
chcp 65001 >nul
title FitAgent MCP Test

echo ============================================
echo  FitAgent MCP Protocol Test (Windows)
echo ============================================
echo.
echo This runs 9 JSON-RPC protocol verification tests.
echo (initialize, tools/list, tools/call, resources/*, prompts/*)
echo.

cd /d "%~dp0..\backend"

python scripts\test_mcp_stdio.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================
    echo  Some tests failed. Check:
    echo    - PYTHONPATH is set to the backend/ directory
    echo    - You are running from the project root
    echo    - MCP_DEMO_USER_ID is set in backend\.env
    echo    - Python dependencies are installed
    echo ============================================
)

cd ..
pause
