#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Rollback Script
# Rolls back to a previous Docker image tag or git commit.
#
# Usage:
#   ./scripts/deploy/rollback.sh                    # rollback to previous image
#   ./scripts/deploy/rollback.sh --tag v1.2.3       # rollback to a specific tag
#   ./scripts/deploy/rollback.sh --list             # list available rollback targets
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TAG=""
LIST=false

for arg in "$@"; do
    case $arg in
        --tag)  shift; TAG="$1" ;;
        --list) LIST=true ;;
    esac
done

log()  { echo -e "${CYAN}[rollback]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}       $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}     $1"; }
die()  { echo -e "${RED}[error]${NC}    $1"; exit 1; }

cd "$ROOT_DIR"

# List available git tags
if [ "$LIST" = true ]; then
    log "Available rollback targets:"
    git -C "$ROOT_DIR" tag --sort=-version:refname | head -20 || echo "  No git tags found"
    echo ""
    log "Running containers:"
    docker compose ps
    exit 0
fi

# Confirmation
warn "Rolling back ALL services to ${TAG:-previous version}."
read -r -p "Type 'yes' to confirm: " CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "Aborted."; exit 1; }

if [ -n "$TAG" ]; then
    log "Checking out tag: $TAG"
    git stash
    git checkout "tags/$TAG" -b "rollback-$TAG-$(date +%s)" || die "Tag $TAG not found"
fi

log "Rebuilding images from current state..."
docker compose build --no-cache backend ai_services

log "Restarting services..."
docker compose up -d --no-deps backend ai_services

sleep 5

HEALTH=$(curl -sf "http://localhost:8000/health" 2>/dev/null || echo "")
if echo "$HEALTH" | grep -q '"status"'; then
    ok "Rollback successful. Backend is healthy."
else
    die "Backend is not responding after rollback. Check: docker compose logs backend"
fi

ok "Rollback complete"
