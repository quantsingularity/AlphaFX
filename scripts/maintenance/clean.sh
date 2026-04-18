#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Clean Build Artifacts
# Removes compiled Python files, logs, coverage reports, and build output.
# Optionally stops and removes Docker containers and volumes.
#
# Usage:
#   ./scripts/maintenance/clean.sh              # clean code artifacts
#   ./scripts/maintenance/clean.sh --docker     # also remove Docker resources
#   ./scripts/maintenance/clean.sh --all        # everything including volumes
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOCKER=false
ALL=false

for arg in "$@"; do
    case $arg in
        --docker) DOCKER=true ;;
        --all)    DOCKER=true; ALL=true ;;
    esac
done

log()  { echo -e "${CYAN}[clean]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}    $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $1"; }

# Python cache
log "Removing Python cache files..."
find "$ROOT_DIR/code" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$ROOT_DIR/code" -name "*.pyc" -delete 2>/dev/null || true
find "$ROOT_DIR/code" -name "*.pyo" -delete 2>/dev/null || true
ok "Python cache cleared"

# Pytest cache
log "Removing pytest cache..."
find "$ROOT_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
ok "Pytest cache cleared"

# Coverage reports
log "Removing coverage reports..."
rm -rf "$ROOT_DIR/coverage" 2>/dev/null || true
ok "Coverage reports removed"

# Log files
log "Removing log files..."
rm -rf "$ROOT_DIR/logs" 2>/dev/null || true
ok "Logs removed"

# Frontend build
log "Removing frontend build output..."
rm -rf "$ROOT_DIR/frontend/dist" 2>/dev/null || true
rm -rf "$ROOT_DIR/frontend/.vite" 2>/dev/null || true
ok "Frontend build output removed"

# Backend static files
log "Removing collected static files..."
rm -rf "$ROOT_DIR/code/backend/staticfiles" 2>/dev/null || true
ok "Static files removed"

# Django SQLite
if [ -f "$ROOT_DIR/code/backend/db.sqlite3" ]; then
    warn "Removing local SQLite database..."
    rm -f "$ROOT_DIR/code/backend/db.sqlite3"
    ok "SQLite database removed"
fi

# Docker
if [ "$DOCKER" = true ]; then
    log "Stopping and removing Docker containers..."
    cd "$ROOT_DIR"
    docker compose down 2>/dev/null || true
    ok "Containers stopped and removed"

    if [ "$ALL" = true ]; then
        warn "Removing Docker volumes (this deletes all database data)..."
        read -r -p "Are you sure? Type 'yes' to confirm: " CONFIRM
        if [ "$CONFIRM" = "yes" ]; then
            docker compose down -v 2>/dev/null || true
            ok "Docker volumes removed"
        else
            log "Volume removal skipped"
        fi
    fi
fi

echo ""
ok "Clean complete"
