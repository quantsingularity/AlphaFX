#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Stop All Local Dev Services
# Kills background processes started by start_all.sh (non-tmux mode)
# or kills the tmux session.
#
# Usage:
#   ./scripts/dev/stop_all.sh
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOGS_DIR="$ROOT_DIR/logs"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${CYAN}[stop]${NC} $1"; }
ok()  { echo -e "${GREEN}[ok]${NC}   $1"; }

# Kill tmux session if it exists
if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t alphafx 2>/dev/null; then
        tmux kill-session -t alphafx
        ok "tmux session 'alphafx' killed"
    fi
fi

# Kill PID-file processes
for service in backend ai_service frontend; do
    PID_FILE="$LOGS_DIR/$service.pid"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            ok "$service (PID $PID) stopped"
        else
            log "$service PID $PID not running"
        fi
        rm -f "$PID_FILE"
    fi
done

# Kill any leftover Django / uvicorn / vite processes by port
for PORT in 8000 8001 5173; do
    PIDS=$(lsof -ti :"$PORT" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
        ok "Cleared port $PORT"
    fi
done

ok "All services stopped"
