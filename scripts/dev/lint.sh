#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Lint and Format Check
# Runs ruff (Python linter), black (formatter check), and tsc (TypeScript).
#
# Usage:
#   ./scripts/dev/lint.sh           # check only
#   ./scripts/dev/lint.sh --fix     # auto-fix where possible
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/code/backend"
AI_DIR="$ROOT_DIR/code/ai_services"
FRONTEND_DIR="$ROOT_DIR/frontend"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

FIX=false
[ "${1:-}" = "--fix" ] && FIX=true

log()  { echo -e "${CYAN}[lint]${NC}  $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}    $1"; }
fail() { echo -e "${RED}[fail]${NC}  $1"; }

RESULT=0

# -----------------------------------------------------------------------------
# Python: ruff
# -----------------------------------------------------------------------------

PYTHON="$BACKEND_DIR/.venv/bin/python"
[ -f "$PYTHON" ] || PYTHON="python3"

log "Installing ruff and black if needed..."
"$PYTHON" -m pip install ruff black --quiet 2>/dev/null || true

log "Running ruff on code/backend..."
if [ "$FIX" = true ]; then
    "$PYTHON" -m ruff check "$BACKEND_DIR/apps" --fix 2>&1 || RESULT=$?
else
    "$PYTHON" -m ruff check "$BACKEND_DIR/apps" 2>&1 || RESULT=$?
fi
[ $RESULT -eq 0 ] && ok "ruff: backend clean" || fail "ruff: backend has issues"

log "Running ruff on code/ai_services..."
if [ "$FIX" = true ]; then
    "$PYTHON" -m ruff check "$AI_DIR" --fix 2>&1 || RESULT=$?
else
    "$PYTHON" -m ruff check "$AI_DIR" 2>&1 || RESULT=$?
fi
[ $RESULT -eq 0 ] && ok "ruff: ai_services clean" || fail "ruff: ai_services has issues"

# -----------------------------------------------------------------------------
# Python: black format check
# -----------------------------------------------------------------------------

log "Running black format check..."
if [ "$FIX" = true ]; then
    "$PYTHON" -m black "$BACKEND_DIR/apps" "$AI_DIR" 2>&1 || true
    ok "black: reformatted files"
else
    "$PYTHON" -m black --check "$BACKEND_DIR/apps" "$AI_DIR" 2>&1 || {
        fail "black: formatting issues found (run with --fix to auto-format)"
        RESULT=1
    }
fi

# -----------------------------------------------------------------------------
# TypeScript: tsc type check
# -----------------------------------------------------------------------------

if command -v npm >/dev/null 2>&1; then
    log "Running TypeScript type check on frontend..."
    cd "$FRONTEND_DIR"
    npx tsc --noEmit 2>&1 || {
        fail "TypeScript: type errors found"
        RESULT=1
    }
    [ $RESULT -eq 0 ] && ok "TypeScript: no type errors"
else
    log "npm not found, skipping TypeScript check"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

echo ""
if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}All lint checks passed.${NC}"
else
    echo -e "${RED}Lint checks failed. Run with --fix to auto-correct Python issues.${NC}"
fi

exit $RESULT
