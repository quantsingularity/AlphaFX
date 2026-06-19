#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Run All Tests
# Executes backend (88 tests) and AI services (20 tests) test suites.
# Generates HTML coverage reports in coverage/ directory.
#
# Usage:
#   ./scripts/dev/run_tests.sh
#   ./scripts/dev/run_tests.sh --backend-only
#   ./scripts/dev/run_tests.sh --ai-only
#   ./scripts/dev/run_tests.sh --no-coverage
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/code/backend"
AI_DIR="$ROOT_DIR/code/ai_services"
COVERAGE_DIR="$ROOT_DIR/coverage"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_ONLY=false
AI_ONLY=false
NO_COVERAGE=false

for arg in "$@"; do
    case $arg in
        --backend-only) BACKEND_ONLY=true ;;
        --ai-only)      AI_ONLY=true ;;
        --no-coverage)  NO_COVERAGE=true ;;
    esac
done

log()  { echo -e "${CYAN}[test]${NC} $1"; }
ok()   { echo -e "${GREEN}[pass]${NC} $1"; }
fail() { echo -e "${RED}[fail]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }

BACKEND_RESULT=0
AI_RESULT=0

# -----------------------------------------------------------------------------
# Backend tests
# -----------------------------------------------------------------------------

if [ "$AI_ONLY" = false ]; then
    log "Running backend test suite (88 tests)..."
    cd "$BACKEND_DIR"

    PYTHON="$BACKEND_DIR/.venv/bin/python"
    [ -f "$PYTHON" ] || PYTHON="python3"

    if [ "$NO_COVERAGE" = false ]; then
        "$PYTHON" -m pip install pytest-cov --quiet 2>/dev/null || true
        "$PYTHON" -m pytest tests/ \
            --tb=short \
            -q \
            --cov=apps \
            --cov-report=term-missing \
            --cov-report="html:$COVERAGE_DIR/backend" \
            2>&1 || BACKEND_RESULT=$?
    else
        "$PYTHON" -m pytest tests/ --tb=short -q 2>&1 || BACKEND_RESULT=$?
    fi

    if [ $BACKEND_RESULT -eq 0 ]; then
        ok "Backend: all tests passed"
    else
        fail "Backend: some tests failed (exit code $BACKEND_RESULT)"
    fi
fi

# -----------------------------------------------------------------------------
# AI services tests
# -----------------------------------------------------------------------------

if [ "$BACKEND_ONLY" = false ]; then
    log "Running AI services test suite (20 tests)..."
    cd "$AI_DIR"

    AI_PYTHON="$AI_DIR/.venv/bin/python"
    [ -f "$AI_PYTHON" ] || AI_PYTHON="python3"

    if [ "$NO_COVERAGE" = false ]; then
        "$AI_PYTHON" -m pip install pytest-cov --quiet 2>/dev/null || true
        "$AI_PYTHON" -m pytest tests/test_ai_services.py \
            --tb=short \
            -q \
            --cov=. \
            --cov-report=term-missing \
            --cov-report="html:$COVERAGE_DIR/ai_services" \
            2>&1 || AI_RESULT=$?
    else
        "$AI_PYTHON" -m pytest tests/test_ai_services.py --tb=short -q 2>&1 || AI_RESULT=$?
    fi

    if [ $AI_RESULT -eq 0 ]; then
        ok "AI services: all tests passed"
    else
        fail "AI services: some tests failed (exit code $AI_RESULT)"
    fi
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

echo ""
echo -e "${CYAN}==============================${NC}"
echo -e "${CYAN} Test Summary${NC}"
echo -e "${CYAN}==============================${NC}"

TOTAL_FAIL=0

if [ "$AI_ONLY" = false ]; then
    if [ $BACKEND_RESULT -eq 0 ]; then
        echo -e "  Backend:     ${GREEN}PASSED${NC}"
    else
        echo -e "  Backend:     ${RED}FAILED${NC}"
        TOTAL_FAIL=1
    fi
fi

if [ "$BACKEND_ONLY" = false ]; then
    if [ $AI_RESULT -eq 0 ]; then
        echo -e "  AI services: ${GREEN}PASSED${NC}"
    else
        echo -e "  AI services: ${RED}FAILED${NC}"
        TOTAL_FAIL=1
    fi
fi

if [ "$NO_COVERAGE" = false ]; then
    echo ""
    echo -e "  Coverage reports:"
    [ "$AI_ONLY" = false ]      && echo -e "    Backend:     ${CYAN}coverage/backend/index.html${NC}"
    [ "$BACKEND_ONLY" = false ] && echo -e "    AI services: ${CYAN}coverage/ai_services/index.html${NC}"
fi

echo ""
exit $TOTAL_FAIL
