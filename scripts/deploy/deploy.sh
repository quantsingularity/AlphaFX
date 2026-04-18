#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Production Deployment Script
# Performs a zero-downtime rolling deployment of all services.
# Runs pre-flight checks, migrations, static collection, and service restarts.
#
# Usage:
#   ./scripts/deploy/deploy.sh
#   ./scripts/deploy/deploy.sh --skip-tests   # skip pre-deploy test run
#   ./scripts/deploy/deploy.sh --service backend  # redeploy a single service
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SKIP_TESTS=false
SERVICE=""
DEPLOY_TIME=$(date +"%Y-%m-%d %H:%M:%S")
VERSION=$(git -C "$ROOT_DIR" describe --tags --always 2>/dev/null || echo "dev")

for arg in "$@"; do
    case $arg in
        --skip-tests) SKIP_TESTS=true ;;
        --service)    shift; SERVICE="$1" ;;
    esac
done

log()  { echo -e "${CYAN}[deploy]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}     $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}   $1"; }
die()  { echo -e "${RED}[error]${NC}  $1"; exit 1; }

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN} AlphaFX Deployment - ${DEPLOY_TIME}${NC}"
echo -e "${CYAN} Version: ${VERSION}${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

cd "$ROOT_DIR"

# -----------------------------------------------------------------------------
# Step 1: Pre-flight checks
# -----------------------------------------------------------------------------

log "Step 1: Pre-flight checks..."

[ -f ".env" ] || die ".env file not found. Copy .env.example and configure it."

SECRET_KEY=$(grep '^SECRET_KEY=' .env | cut -d'=' -f2- | tr -d '"')
[ "$SECRET_KEY" = "change-me-in-production" ] || [ -z "$SECRET_KEY" ] && \
    die "SECRET_KEY is not set or is the default. Set a secure value in .env."

DEBUG=$(grep '^DEBUG=' .env | cut -d'=' -f2- | tr -d '"' || echo "False")
[ "$DEBUG" = "True" ] && warn "DEBUG=True in production is not recommended"

command -v docker >/dev/null 2>&1 || die "Docker is required"
command -v docker compose >/dev/null 2>&1 || die "Docker Compose is required"

ok "Pre-flight checks passed"

# -----------------------------------------------------------------------------
# Step 2: Run tests (optional)
# -----------------------------------------------------------------------------

if [ "$SKIP_TESTS" = false ]; then
    log "Step 2: Running test suite..."
    "$ROOT_DIR/scripts/dev/run_tests.sh" --no-coverage || die "Tests failed. Aborting deployment."
    ok "All tests passed"
else
    warn "Step 2: Skipping tests (--skip-tests)"
fi

# -----------------------------------------------------------------------------
# Step 3: Build images
# -----------------------------------------------------------------------------

log "Step 3: Building Docker images..."
if [ -n "$SERVICE" ]; then
    docker compose build "$SERVICE"
else
    docker compose build
fi
ok "Images built"

# -----------------------------------------------------------------------------
# Step 4: Database migrations
# -----------------------------------------------------------------------------

log "Step 4: Running database migrations..."
docker compose run --rm backend python manage.py migrate --noinput
ok "Migrations applied"

# -----------------------------------------------------------------------------
# Step 5: Collect static files
# -----------------------------------------------------------------------------

log "Step 5: Collecting static files..."
docker compose run --rm backend python manage.py collectstatic --noinput --clear 2>/dev/null
ok "Static files collected"

# -----------------------------------------------------------------------------
# Step 6: Rolling restart
# -----------------------------------------------------------------------------

log "Step 6: Restarting services..."
if [ -n "$SERVICE" ]; then
    docker compose up -d --no-deps "$SERVICE"
    ok "Service '$SERVICE' restarted"
else
    # Restart in dependency order: backend first, then ai_services, then frontend, then nginx
    for svc in backend ai_services frontend nginx; do
        log "  Restarting $svc..."
        docker compose up -d --no-deps "$svc"
        sleep 3
    done
    ok "All services restarted"
fi

# -----------------------------------------------------------------------------
# Step 7: Health check
# -----------------------------------------------------------------------------

log "Step 7: Health check..."
sleep 5

HEALTH=$(curl -sf "http://localhost:8000/health" 2>/dev/null || echo "")
if echo "$HEALTH" | grep -q '"status"'; then
    ok "Backend health check passed"
else
    warn "Backend health check did not respond - check logs with: docker compose logs backend"
fi

AI_HEALTH=$(curl -sf "http://localhost:8001/ai/health" 2>/dev/null || echo "")
if echo "$AI_HEALTH" | grep -q '"status"'; then
    ok "AI service health check passed"
else
    warn "AI service health check did not respond - it may still be initialising"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN} Deployment complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  Platform:    ${CYAN}http://localhost${NC}"
echo -e "  API docs:    ${CYAN}http://localhost:8000/docs/${NC}"
echo -e "  AI service:  ${CYAN}http://localhost:8001/docs${NC}"
echo -e "  Admin:       ${CYAN}http://localhost:8000/admin/${NC}"
echo -e "  Version:     ${CYAN}${VERSION}${NC}"
echo ""
