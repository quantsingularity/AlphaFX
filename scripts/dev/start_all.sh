#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Start All Services (Local Development)
# Starts Django, AI service, and frontend dev server in parallel,
# each in its own tmux pane (or background processes if tmux is absent).
#
# Usage:
#   ./scripts/dev/start_all.sh
#   ./scripts/dev/start_all.sh --no-ai      # skip AI service
#   ./scripts/dev/start_all.sh --no-frontend # skip frontend
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/code/backend"
AI_DIR="$ROOT_DIR/code/ai_services"
FRONTEND_DIR="$ROOT_DIR/frontend"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

SKIP_AI=false
SKIP_FRONTEND=false

for arg in "$@"; do
    case $arg in
        --no-ai)       SKIP_AI=true ;;
        --no-frontend) SKIP_FRONTEND=true ;;
    esac
done

log() { echo -e "${CYAN}[start]${NC} $1"; }
ok()  { echo -e "${GREEN}[ok]${NC}    $1"; }

# Check virtual environments exist
[ -f "$BACKEND_DIR/.venv/bin/python" ] || {
    echo "Backend venv not found. Run ./scripts/dev/setup.sh first."
    exit 1
}

# Log files
LOGS_DIR="$ROOT_DIR/logs"
mkdir -p "$LOGS_DIR"

if command -v tmux >/dev/null 2>&1; then
    # ------------------------------------
    # tmux session (preferred)
    # ------------------------------------
    SESSION="alphafx"
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    tmux new-session -d -s "$SESSION" -n "backend" \
        "cd $BACKEND_DIR && .venv/bin/python manage.py runserver 0.0.0.0:8000 2>&1 | tee $LOGS_DIR/backend.log"

    if [ "$SKIP_AI" = false ]; then
        tmux new-window -t "$SESSION" -n "ai_service" \
            "cd $AI_DIR && .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload 2>&1 | tee $LOGS_DIR/ai_service.log"
    fi

    if [ "$SKIP_FRONTEND" = false ]; then
        tmux new-window -t "$SESSION" -n "frontend" \
            "cd $FRONTEND_DIR && npm run dev 2>&1 | tee $LOGS_DIR/frontend.log"
    fi

    tmux select-window -t "$SESSION:backend"
    ok "tmux session 'alphafx' started. Attach with: tmux attach -t alphafx"

else
    # ------------------------------------
    # Background processes fallback
    # ------------------------------------
    log "tmux not found, starting services as background processes..."
    log "Logs will be written to ./logs/"

    cd "$BACKEND_DIR"
    .venv/bin/python manage.py runserver 0.0.0.0:8000 > "$LOGS_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    ok "Backend started (PID $BACKEND_PID) -> http://localhost:8000"

    if [ "$SKIP_AI" = false ] && [ -f "$AI_DIR/.venv/bin/uvicorn" ]; then
        cd "$AI_DIR"
        .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload > "$LOGS_DIR/ai_service.log" 2>&1 &
        AI_PID=$!
        ok "AI service started (PID $AI_PID) -> http://localhost:8001"
    fi

    if [ "$SKIP_FRONTEND" = false ]; then
        cd "$FRONTEND_DIR"
        npm run dev > "$LOGS_DIR/frontend.log" 2>&1 &
        FE_PID=$!
        ok "Frontend started (PID $FE_PID) -> http://localhost:5173"
    fi

    echo ""
    echo -e "${GREEN}All services running. Logs in ./logs/${NC}"
    echo "Stop with: ./scripts/dev/stop_all.sh"
    echo ""

    # Save PIDs
    echo "$BACKEND_PID" > "$LOGS_DIR/backend.pid"
    [ -n "${AI_PID:-}" ] && echo "$AI_PID" > "$LOGS_DIR/ai_service.pid"
    [ -n "${FE_PID:-}" ] && echo "$FE_PID" > "$LOGS_DIR/frontend.pid"
fi
