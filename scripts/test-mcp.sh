#!/usr/bin/env bash
# FitAgent MCP Protocol Test (macOS / Linux)
# Usage: chmod +x scripts/test-mcp.sh && ./scripts/test-mcp.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
PYTHON=$(command -v python3 || command -v python)

echo "============================================"
echo " FitAgent MCP Protocol Test (macOS/Linux)"
echo "============================================"
echo ""
echo "Running 9 JSON-RPC protocol verification tests..."
echo ""

cd "$BACKEND_DIR"
$PYTHON scripts/test_mcp_stdio.py
RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo ""
    echo "============================================"
    echo " Some tests failed. Check:"
    echo "   - PYTHONPATH is set to the backend/ directory"
    echo "   - MCP_DEMO_USER_ID is set in backend/.env"
    echo "   - Python dependencies are installed"
    echo "============================================"
fi

cd "$PROJECT_DIR"
exit $RESULT
