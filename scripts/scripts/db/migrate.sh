#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Database Migration Runner
# Runs Django migrations with safety checks.
# Supports local venv and Docker Compose targets.
#
# Usage:
#   ./scripts/db/migrate.sh                  # local venv
#   ./scripts/db/migrate.sh --docker         # via docker compose exec
#   ./scripts/db/migrate.sh --check          # check without applying
#   ./scripts/db/migrate.sh --app portfolio  # migrate a single app
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/code/backend"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

MODE="local"
CHECK_ONLY=false
APP=""

for arg in "$@"; do
    case $arg in
        --docker) MODE="docker" ;;
        --check)  CHECK_ONLY=true ;;
        --app)    shift; APP="$1" ;;
    esac
done

log()  { echo -e "${CYAN}[migrate]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}      $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}    $1"; }

# -----------------------------------------------------------------------------
# Helper: run a manage.py command
# -----------------------------------------------------------------------------

run_manage() {
    local CMD="$*"
    if [ "$MODE" = "docker" ]; then
        docker compose exec backend python manage.py $CMD
    else
        PYTHON="$BACKEND_DIR/.venv/bin/python"
        [ -f "$PYTHON" ] || PYTHON="python3"
        cd "$BACKEND_DIR"
        "$PYTHON" manage.py $CMD
    fi
}

# -----------------------------------------------------------------------------
# Show pending migrations
# -----------------------------------------------------------------------------

log "Checking pending migrations..."
run_manage showmigrations --list 2>&1 | grep '\[ \]' && warn "Unapplied migrations found" || ok "No pending migrations"

if [ "$CHECK_ONLY" = true ]; then
    log "Check-only mode, exiting without applying"
    exit 0
fi

# -----------------------------------------------------------------------------
# Apply migrations
# -----------------------------------------------------------------------------

if [ -n "$APP" ]; then
    log "Migrating app: $APP"
    run_manage migrate "$APP" --noinput
else
    log "Applying all migrations..."
    run_manage migrate --noinput
fi

ok "Migrations complete"

# -----------------------------------------------------------------------------
# Show final migration state
# -----------------------------------------------------------------------------

log "Final migration state:"
run_manage showmigrations
