#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Dependency Update Checker
# Reports outdated Python and Node.js dependencies across all packages.
#
# Usage:
#   ./scripts/maintenance/check_updates.sh
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${CYAN}[updates]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}      $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}    $1"; }

# -----------------------------------------------------------------------------
# Backend Python
# -----------------------------------------------------------------------------

log "Checking backend Python dependencies..."
BACKEND_PYTHON="$ROOT_DIR/code/backend/.venv/bin/python"
[ -f "$BACKEND_PYTHON" ] || BACKEND_PYTHON="python3"

"$BACKEND_PYTHON" -m pip install pip-outdated --quiet 2>/dev/null || \
    "$BACKEND_PYTHON" -m pip install --upgrade pip --quiet

echo ""
echo "Backend (code/backend/requirements.txt):"
"$BACKEND_PYTHON" -m pip list --outdated --format=columns 2>/dev/null | head -30 || true

# -----------------------------------------------------------------------------
# AI services Python
# -----------------------------------------------------------------------------

echo ""
log "Checking AI services Python dependencies..."
AI_PYTHON="$ROOT_DIR/code/ai_services/.venv/bin/python"
[ -f "$AI_PYTHON" ] || AI_PYTHON="python3"

echo "AI services (code/ai_services/requirements.txt):"
"$AI_PYTHON" -m pip list --outdated --format=columns 2>/dev/null | head -30 || true

# -----------------------------------------------------------------------------
# Frontend npm
# -----------------------------------------------------------------------------

echo ""
log "Checking frontend npm dependencies..."
cd "$ROOT_DIR/frontend"

if command -v npm >/dev/null 2>&1; then
    echo "Frontend (frontend/package.json):"
    npm outdated 2>/dev/null | head -30 || echo "  All dependencies up to date"
else
    warn "npm not found, skipping frontend check"
fi

echo ""
ok "Dependency check complete"
echo ""
warn "Always test after updating dependencies. Run ./scripts/dev/run_tests.sh after upgrading."
