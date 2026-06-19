#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - AI Model Training Script
# Trains LSTM, HMM regime, GARCH, and anomaly detection models
# for a specified set of currency pairs.
#
# Usage:
#   ./scripts/ai/train_models.sh                        # all major pairs
#   ./scripts/ai/train_models.sh --pairs EURUSD GBPUSD  # specific pairs
#   ./scripts/ai/train_models.sh --docker               # via Docker Compose
#   ./scripts/ai/train_models.sh --lookback 90          # custom lookback
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AI_DIR="$ROOT_DIR/code/ai_services"
MODEL_DIR="$AI_DIR/saved_models"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

MODE="local"
PAIRS="all"
LOOKBACK=60

while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)   MODE="docker"; shift ;;
        --lookback) LOOKBACK="$2"; shift 2 ;;
        --pairs)    shift; PAIRS=""; while [[ $# -gt 0 && $1 != --* ]]; do PAIRS="$PAIRS $1"; shift; done ;;
        *) shift ;;
    esac
done

log()  { echo -e "${CYAN}[train]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}    $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $1"; }

echo ""
log "AlphaFX AI Model Training"
log "Pairs:    ${PAIRS:-all major pairs}"
log "Lookback: ${LOOKBACK} bars"
log "Mode:     ${MODE}"
log "Output:   $MODEL_DIR"
echo ""

# Install optional ML dependencies
install_optional() {
    local PYTHON="$1"
    log "Checking optional ML dependencies..."

    for pkg in hmmlearn arch; do
        if ! "$PYTHON" -c "import $pkg" 2>/dev/null; then
            log "Installing $pkg..."
            "$PYTHON" -m pip install "$pkg" --quiet && ok "$pkg installed" || \
                warn "$pkg installation failed (some models will be skipped)"
        else
            ok "$pkg already installed"
        fi
    done
}

if [ "$MODE" = "docker" ]; then
    log "Training via Docker Compose (ai_services container)..."
    PAIR_ARGS="$PAIRS"
    [ "$PAIRS" = "all" ] && PAIR_ARGS="all"
    docker compose exec ai_services python -m training.train_all \
        --pairs $PAIR_ARGS \
        --output-dir /app/saved_models \
        --lookback "$LOOKBACK"
else
    AI_PYTHON="$AI_DIR/.venv/bin/python"
    [ -f "$AI_PYTHON" ] || AI_PYTHON="python3"

    install_optional "$AI_PYTHON"

    mkdir -p "$MODEL_DIR"
    log "Starting training pipeline..."

    cd "$AI_DIR"
    PAIR_ARGS="$PAIRS"
    [ "$PAIRS" = "all" ] && PAIR_ARGS="all"

    "$AI_PYTHON" -m training.train_all \
        --pairs $PAIR_ARGS \
        --output-dir "$MODEL_DIR" \
        --lookback "$LOOKBACK"
fi

echo ""
ok "Training complete. Models saved to: $MODEL_DIR"
echo ""

# Show manifest
MANIFEST="$MODEL_DIR/training_manifest.json"
if [ -f "$MANIFEST" ]; then
    log "Training manifest:"
    python3 -c "
import json
with open('$MANIFEST') as f:
    m = json.load(f)
print(f'  Trained at: {m[\"trained_at\"]}')
print(f'  Pairs:      {len(m[\"pairs\"])}')
print()
for r in m.get('metrics', []):
    status  = r.get('status', 'unknown')
    pair    = r.get('pair', '?')
    val_acc = r.get('lstm_val_acc', 'N/A')
    regime  = r.get('regime', 'N/A')
    print(f'  {pair}: status={status}, lstm_val_acc={val_acc}, regime={regime}')
" 2>/dev/null || true
fi
