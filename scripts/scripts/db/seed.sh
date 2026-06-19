#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Database Seeder
# Populates the database with realistic sample portfolios, positions,
# and price alerts for development and demo purposes.
#
# Usage:
#   ./scripts/db/seed.sh
#   ./scripts/db/seed.sh --docker
#   ./scripts/db/seed.sh --reset     # clear existing data first
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/code/backend"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

MODE="local"
RESET=false

for arg in "$@"; do
    case $arg in
        --docker) MODE="docker" ;;
        --reset)  RESET=true ;;
    esac
done

log() { echo -e "${CYAN}[seed]${NC} $1"; }
ok()  { echo -e "${GREEN}[ok]${NC}   $1"; }

# -----------------------------------------------------------------------------
# Seed script (Python)
# -----------------------------------------------------------------------------

SEED_SCRIPT=$(cat <<'PYEOF'
import os
import django
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alphafx.settings.base")
django.setup()

from apps.portfolio.models import Portfolio, Position, PriceAlert

if "--reset" in sys.argv:
    print("  Clearing existing data...")
    TradeHistory = None
    try:
        from apps.portfolio.models import TradeHistory
        TradeHistory.objects.all().delete()
    except Exception:
        pass
    Position.objects.all().delete()
    PriceAlert.objects.all().delete()
    Portfolio.objects.all().delete()
    print("  Existing data cleared")

# ------------------------------------------------------------------
# Portfolios
# ------------------------------------------------------------------

PORTFOLIOS = [
    {"name": "Trend Following Fund",    "base_currency": "USD", "initial_balance": 500_000,
     "description": "Momentum-based directional strategy across G10 pairs"},
    {"name": "Carry Trade Portfolio",   "base_currency": "USD", "initial_balance": 250_000,
     "description": "Long high-yield, short low-yield currency pairs"},
    {"name": "Macro Hedging Book",      "base_currency": "USD", "initial_balance": 1_000_000,
     "description": "FX risk hedges for a multi-asset global macro portfolio"},
]

created_portfolios = []
for p_data in PORTFOLIOS:
    p, created = Portfolio.objects.get_or_create(name=p_data["name"], defaults=p_data)
    created_portfolios.append(p)
    status = "created" if created else "already exists"
    print(f"  Portfolio '{p.name}': {status}")

# ------------------------------------------------------------------
# Positions
# ------------------------------------------------------------------

POSITIONS = [
    # Trend Following Fund
    {"portfolio_name": "Trend Following Fund",  "pair": "EURUSD", "side": "buy",
     "notional": 200_000, "entry_rate": 1.0820, "stop_loss": 1.0750, "take_profit": 1.0950, "leverage": 5.0},
    {"portfolio_name": "Trend Following Fund",  "pair": "GBPUSD", "side": "buy",
     "notional": 150_000, "entry_rate": 1.2580, "stop_loss": 1.2480, "take_profit": 1.2780, "leverage": 5.0},
    {"portfolio_name": "Trend Following Fund",  "pair": "USDJPY", "side": "sell",
     "notional": 100_000, "entry_rate": 155.20, "stop_loss": 156.50, "take_profit": 152.00, "leverage": 3.0},
    # Carry Trade Portfolio
    {"portfolio_name": "Carry Trade Portfolio", "pair": "USDTRY", "side": "buy",
     "notional": 50_000,  "entry_rate": 31.80,  "stop_loss": 33.00,  "take_profit": 30.00,  "leverage": 2.0},
    {"portfolio_name": "Carry Trade Portfolio", "pair": "NZDUSD", "side": "buy",
     "notional": 80_000,  "entry_rate": 0.5950, "stop_loss": 0.5850, "take_profit": 0.6150, "leverage": 4.0},
    {"portfolio_name": "Carry Trade Portfolio", "pair": "USDJPY", "side": "buy",
     "notional": 120_000, "entry_rate": 153.80, "stop_loss": 151.00, "take_profit": 158.00, "leverage": 3.0},
    # Macro Hedging Book
    {"portfolio_name": "Macro Hedging Book",    "pair": "EURUSD", "side": "sell",
     "notional": 300_000, "entry_rate": 1.0900, "stop_loss": 1.1050, "take_profit": 1.0650, "leverage": 2.0},
    {"portfolio_name": "Macro Hedging Book",    "pair": "USDCHF", "side": "buy",
     "notional": 200_000, "entry_rate": 0.9050, "stop_loss": 0.8950, "take_profit": 0.9200, "leverage": 2.0},
]

portfolio_map = {p.name: p for p in created_portfolios}

for pos_data in POSITIONS:
    portfolio_name = pos_data.pop("portfolio_name")
    portfolio = portfolio_map.get(portfolio_name)
    if portfolio is None:
        print(f"  WARNING: portfolio '{portfolio_name}' not found, skipping position")
        continue
    pos_data["portfolio"] = portfolio
    pos_data["status"] = "open"
    Position.objects.get_or_create(
        portfolio=portfolio, pair=pos_data["pair"], entry_rate=pos_data["entry_rate"],
        defaults=pos_data
    )
    print(f"  Position: {pos_data['side'].upper()} {pos_data['pair']} in '{portfolio_name}'")

# ------------------------------------------------------------------
# Price alerts
# ------------------------------------------------------------------

ALERTS = [
    {"pair": "EURUSD", "target_price": 1.0950, "condition": "above",
     "message": "EUR/USD breakout above key resistance"},
    {"pair": "EURUSD", "target_price": 1.0750, "condition": "below",
     "message": "EUR/USD breakdown below support"},
    {"pair": "USDJPY", "target_price": 158.00, "condition": "above",
     "message": "USD/JPY intervention risk level"},
    {"pair": "GBPUSD", "target_price": 1.2500, "condition": "below",
     "message": "GBP/USD key psychological support"},
    {"pair": "USDTRY", "target_price": 35.00,  "condition": "above",
     "message": "USD/TRY all-time high breach"},
]

for a_data in ALERTS:
    PriceAlert.objects.get_or_create(
        pair=a_data["pair"], target_price=a_data["target_price"],
        condition=a_data["condition"], defaults=a_data
    )
    print(f"  Alert: {a_data['pair']} {a_data['condition']} {a_data['target_price']}")

print("")
print(f"Seed complete: {Portfolio.objects.count()} portfolios, "
      f"{Position.objects.filter(status='open').count()} open positions, "
      f"{PriceAlert.objects.count()} alerts")
PYEOF
)

# Write the seed script to a temp file
TMP_SEED=$(mktemp /tmp/alphafx_seed_XXXX.py)
echo "$SEED_SCRIPT" > "$TMP_SEED"
[ "$RESET" = true ] && echo "RESET_ARG=--reset" || echo "RESET_ARG="

# -----------------------------------------------------------------------------
# Execute
# -----------------------------------------------------------------------------

if [ "$MODE" = "docker" ]; then
    log "Running seeder via Docker Compose..."
    docker compose exec -T backend python - < "$TMP_SEED"
else
    log "Running seeder locally..."
    PYTHON="$BACKEND_DIR/.venv/bin/python"
    [ -f "$PYTHON" ] || PYTHON="python3"
    cd "$BACKEND_DIR"
    if [ "$RESET" = true ]; then
        "$PYTHON" "$TMP_SEED" --reset
    else
        "$PYTHON" "$TMP_SEED"
    fi
fi

rm -f "$TMP_SEED"
ok "Database seeding complete"
