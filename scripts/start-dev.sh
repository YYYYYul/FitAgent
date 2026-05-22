#!/usr/bin/env bash
# FitAgent — Local Dev Startup (macOS / Linux)
# Usage: chmod +x scripts/start-dev.sh && ./scripts/start-dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo " FitAgent — Local Dev Startup (macOS/Linux)"
echo "============================================"
echo ""

# ---- Python check ----
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "[ERROR] Python not found. Install Python 3.10+."
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)
echo "[OK] Python: $($PYTHON --version)"

# ---- Node check ----
if ! command -v node &>/dev/null; then
    echo "[ERROR] Node.js not found. Install Node.js 18+."
    exit 1
fi
echo "[OK] Node: $(node --version)"

# ---- .env check ----
if [ ! -f "$PROJECT_DIR/backend/.env" ]; then
    echo "[WARN] backend/.env not found."
    echo "       The system can start but may not work correctly."
    echo ""
fi

# ---- Database check ----
if [ ! -f "$PROJECT_DIR/backend/fitagent.db" ]; then
    echo "[WARN] Database not found. Running migration..."
    cd "$PROJECT_DIR/backend"
    $PYTHON -m alembic upgrade head
    cd "$PROJECT_DIR"
    echo "[OK]   Database created."
    echo ""
fi

# ---- Environment check ----
echo "Running environment check..."
$PYTHON "$PROJECT_DIR/scripts/check-env.py"
echo ""

# ---- Start Backend ----
echo "Starting Backend (FastAPI :8001)..."
cd "$PROJECT_DIR/backend"
$PYTHON -m uvicorn app.main:app --port 8001 &
BACKEND_PID=$!
cd "$PROJECT_DIR"

sleep 3

# ---- Start Frontend ----
echo "Starting Frontend (Next.js :3000)..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
cd "$PROJECT_DIR"

echo ""
echo "============================================"
echo " Both services running."
echo ""
echo " Frontend:   http://localhost:3000"
echo " Backend:    http://localhost:8001"
echo " API Docs:   http://localhost:8001/docs"
echo " Health:     http://localhost:8001/health"
echo ""
echo " Press Ctrl+C to stop both services."
echo "============================================"

# Trap Ctrl+C to kill both
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
