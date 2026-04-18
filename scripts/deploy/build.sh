#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Docker Build Script
# Builds all Docker images for the platform.
# Optionally tags and pushes to a container registry.
#
# Usage:
#   ./scripts/deploy/build.sh
#   ./scripts/deploy/build.sh --no-cache
#   ./scripts/deploy/build.sh --push --registry registry.example.com/alphafx
#   ./scripts/deploy/build.sh --service backend    # build a single service
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

NO_CACHE=false
PUSH=false
REGISTRY=""
SERVICE=""
VERSION=$(git -C "$ROOT_DIR" describe --tags --always 2>/dev/null || echo "dev")

for arg in "$@"; do
    case $arg in
        --no-cache)  NO_CACHE=true ;;
        --push)      PUSH=true ;;
        --registry)  shift; REGISTRY="$1" ;;
        --service)   shift; SERVICE="$1" ;;
    esac
done

log()  { echo -e "${CYAN}[build]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}    $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $1"; }

cd "$ROOT_DIR"

# Build args
COMPOSE_ARGS="--build"
[ "$NO_CACHE" = true ] && COMPOSE_ARGS="$COMPOSE_ARGS --no-cache"

# -----------------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------------

if [ -n "$SERVICE" ]; then
    log "Building service: $SERVICE (version: $VERSION)"
    docker compose build $COMPOSE_ARGS "$SERVICE"
    ok "$SERVICE built successfully"
else
    log "Building all services (version: $VERSION)..."
    docker compose build $COMPOSE_ARGS
    ok "All services built successfully"
fi

# -----------------------------------------------------------------------------
# Tag and push
# -----------------------------------------------------------------------------

if [ "$PUSH" = true ] && [ -n "$REGISTRY" ]; then
    SERVICES=("backend" "ai_services" "frontend")
    [ -n "$SERVICE" ] && SERVICES=("$SERVICE")

    for svc in "${SERVICES[@]}"; do
        LOCAL_TAG="alphafx-${svc}:latest"
        REMOTE_TAG="${REGISTRY}/${svc}:${VERSION}"
        REMOTE_LATEST="${REGISTRY}/${svc}:latest"

        log "Tagging $LOCAL_TAG -> $REMOTE_TAG"
        docker tag "$LOCAL_TAG" "$REMOTE_TAG" 2>/dev/null || warn "Could not tag $svc (image may not exist)"

        log "Pushing $REMOTE_TAG..."
        docker push "$REMOTE_TAG" && ok "Pushed $REMOTE_TAG"

        docker tag "$LOCAL_TAG" "$REMOTE_LATEST" 2>/dev/null || true
        docker push "$REMOTE_LATEST" 2>/dev/null && ok "Pushed $REMOTE_LATEST" || true
    done
fi

# -----------------------------------------------------------------------------
# Image sizes
# -----------------------------------------------------------------------------

echo ""
log "Image sizes:"
docker images | grep -E "alphafx|REPOSITORY" || true
