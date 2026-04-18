#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Platform Health Check
# Checks the status of all running services and reports any issues.
# Suitable for use as a cron job or monitoring script.
#
# Usage:
#   ./scripts/maintenance/health_check.sh
#   ./scripts/maintenance/health_check.sh --json   # machine-readable output
#   ./scripts/maintenance/health_check.sh --slack  # post to Slack webhook
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

JSON_MODE=false
SLACK_WEBHOOK=""

for arg in "$@"; do
    case $arg in
        --json)  JSON_MODE=true ;;
        --slack) shift; SLACK_WEBHOOK="${1:-}" ;;
    esac
done

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
OVERALL_STATUS="healthy"
declare -A RESULTS

check() {
    local NAME="$1"
    local URL="$2"
    local FIELD="$3"

    HTTP_CODE=$(curl -o /tmp/hc_response.json -w "%{http_code}" -sf --max-time 5 "$URL" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
        VALUE=$(python3 -c "import json; d=json.load(open('/tmp/hc_response.json')); print(d.get('$FIELD','unknown'))" 2>/dev/null || echo "unknown")
        RESULTS["$NAME"]="ok ($VALUE)"
        [ "$JSON_MODE" = false ] && echo -e "  ${GREEN}[ok]${NC}   $NAME: $VALUE"
    else
        RESULTS["$NAME"]="FAILED (HTTP $HTTP_CODE)"
        OVERALL_STATUS="degraded"
        [ "$JSON_MODE" = false ] && echo -e "  ${RED}[FAIL]${NC} $NAME: HTTP $HTTP_CODE"
    fi
}

check_docker() {
    local NAME="$1"
    local SERVICE="$2"
    STATUS=$(docker compose ps --status running --services 2>/dev/null | grep "^$SERVICE$" || echo "")
    if [ -n "$STATUS" ]; then
        RESULTS["docker_$NAME"]="running"
        [ "$JSON_MODE" = false ] && echo -e "  ${GREEN}[ok]${NC}   Docker $NAME: running"
    else
        RESULTS["docker_$NAME"]="not running"
        OVERALL_STATUS="degraded"
        [ "$JSON_MODE" = false ] && echo -e "  ${RED}[FAIL]${NC} Docker $NAME: not running"
    fi
}

# -----------------------------------------------------------------------------
# Run checks
# -----------------------------------------------------------------------------

[ "$JSON_MODE" = false ] && {
    echo ""
    echo -e "${CYAN}=============================="
    echo -e " AlphaFX Health Check"
    echo -e " $TIMESTAMP"
    echo -e "==============================${NC}"
    echo ""
    echo "HTTP endpoints:"
}

check "backend_root"   "http://localhost:8000/"           "status"
check "backend_health" "http://localhost:8000/health"     "status"
check "ai_health"      "http://localhost:8001/ai/health"  "status"

[ "$JSON_MODE" = false ] && echo ""
[ "$JSON_MODE" = false ] && echo "Docker containers:"

if command -v docker >/dev/null 2>&1; then
    check_docker "backend"     "backend"
    check_docker "ai_services" "ai_services"
    check_docker "frontend"    "frontend"
    check_docker "db"          "db"
    check_docker "redis"       "redis"
    check_docker "nginx"       "nginx"
fi

# -----------------------------------------------------------------------------
# Output
# -----------------------------------------------------------------------------

if [ "$JSON_MODE" = true ]; then
    python3 -c "
import json, sys
results = $( declare -p RESULTS )
print('nope')
" 2>/dev/null || true

    echo "{"
    echo "  \"timestamp\": \"$TIMESTAMP\","
    echo "  \"overall\": \"$OVERALL_STATUS\","
    echo "  \"checks\": {"
    FIRST=true
    for key in "${!RESULTS[@]}"; do
        [ "$FIRST" = false ] && echo ","
        echo -n "    \"$key\": \"${RESULTS[$key]}\""
        FIRST=false
    done
    echo ""
    echo "  }"
    echo "}"
else
    echo ""
    if [ "$OVERALL_STATUS" = "healthy" ]; then
        echo -e "${GREEN}Overall status: HEALTHY${NC}"
    else
        echo -e "${RED}Overall status: DEGRADED${NC}"
        echo -e "${YELLOW}Check 'docker compose logs' for details${NC}"
    fi
    echo ""
fi

# -----------------------------------------------------------------------------
# Slack notification (if webhook set and status is degraded)
# -----------------------------------------------------------------------------

if [ -n "$SLACK_WEBHOOK" ] && [ "$OVERALL_STATUS" != "healthy" ]; then
    PAYLOAD="{\"text\": \"AlphaFX Health Alert ($TIMESTAMP): Status is DEGRADED. Check the platform immediately.\"}"
    curl -s -X POST -H 'Content-type: application/json' --data "$PAYLOAD" "$SLACK_WEBHOOK" >/dev/null || true
fi

[ "$OVERALL_STATUS" = "healthy" ] && exit 0 || exit 1
