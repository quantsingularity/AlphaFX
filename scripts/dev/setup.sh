#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Local Development Setup
# Bootstraps the full development environment from scratch.
# Run once after cloning the repository.
#
# Usage:
#   chmod +x scripts/dev/setup.sh
#   ./scripts/dev/setup.sh
# -----------------------------------------------------------------------------

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

log()    { echo -e "${CYAN}[setup]${NC} $1"; }
ok()     { echo -e "${GREEN}[ok]${NC}    $1"; }
warn()   { echo -e "${YELLOW}[warn]${NC}  $1"; }
die()    { echo -e "${RED}[error]${NC} $1"; exit 1; }

# -----------------------------------------------------------------------------
# 1. Prerequisites check
# -----------------------------------------------------------------------------

log "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || die "Python 3.12+ is required. Install from https://python.org"
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log "Python version: $PYVER"

command -v node >/dev/null 2>&1 || die "Node.js 20+ is required. Install from https://nodejs.org"
NODEVER=$(node --version)
log "Node.js version: $NODEVER"

command -v git >/dev/null 2>&1 || die "Git is required."

# -----------------------------------------------------------------------------
# 2. Environment file
# -----------------------------------------------------------------------------

log "Setting up environment file..."
if [ ! -f "$ROOT_DIR/.env" ]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    # Patch for local dev: use SQLite
    sed -i 's|DATABASE_URL=postgresql://.*|DATABASE_URL=sqlite:///db.sqlite3|' "$ROOT_DIR/.env"
    ok ".env created from .env.example (SQLite configured for local dev)"
else
    warn ".env already exists, skipping"
fi

# -----------------------------------------------------------------------------
# 3. Backend Python virtual environment
# -----------------------------------------------------------------------------

log "Setting up backend virtual environment..."
BACKEND_DIR="$ROOT_DIR/code/backend"
VENV_DIR="$BACKEND_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created at code/backend/.venv"
else
    warn "Virtual environment already exists, skipping creation"
fi

log "Installing backend Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt" --quiet
ok "Backend dependencies installed"

# -----------------------------------------------------------------------------
# 4. Django setup
# -----------------------------------------------------------------------------

log "Running Django migrations..."
cd "$BACKEND_DIR"
"$VENV_DIR/bin/python" manage.py migrate --noinput
ok "Database migrations applied"

log "Collecting static files..."
"$VENV_DIR/bin/python" manage.py collectstatic --noinput --clear 2>/dev/null || true
ok "Static files collected"

# Offer superuser creation
echo ""
read -r -p "Create Django admin superuser? [y/N] " CREATE_SUPER
if [[ "$CREATE_SUPER" =~ ^[Yy]$ ]]; then
    "$VENV_DIR/bin/python" manage.py createsuperuser
fi

# -----------------------------------------------------------------------------
# 5. AI services virtual environment
# -----------------------------------------------------------------------------

log "Setting up AI services virtual environment..."
AI_DIR="$ROOT_DIR/code/ai_services"
AI_VENV="$AI_DIR/.venv"

if [ ! -d "$AI_VENV" ]; then
    python3 -m venv "$AI_VENV"
    ok "AI venv created at code/ai_services/.venv"
fi

log "Installing AI services dependencies (core only, no PyTorch)..."
"$AI_VENV/bin/pip" install --upgrade pip --quiet
"$AI_VENV/bin/pip" install scikit-learn numpy pandas scipy statsmodels fastapi uvicorn pydantic joblib httpx --quiet
ok "AI services core dependencies installed"
warn "To enable LSTM/Transformer models, run: pip install torch (in code/ai_services/.venv)"
warn "To enable GARCH models, run: pip install arch (in code/ai_services/.venv)"
warn "To enable HMM regime detection, run: pip install hmmlearn (in code/ai_services/.venv)"

# -----------------------------------------------------------------------------
# 6. Frontend
# -----------------------------------------------------------------------------

log "Installing frontend dependencies..."
cd "$ROOT_DIR/frontend"
npm install --silent
ok "Frontend dependencies installed"

# -----------------------------------------------------------------------------
# 7. Summary
# -----------------------------------------------------------------------------

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN} AlphaFX development environment is ready!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  Start backend:     ${CYAN}cd code/backend && .venv/bin/python manage.py runserver${NC}"
echo -e "  Start AI service:  ${CYAN}cd code/ai_services && .venv/bin/uvicorn api.main:app --port 8001${NC}"
echo -e "  Start frontend:    ${CYAN}cd frontend && npm run dev${NC}"
echo ""
echo -e "  Or run everything: ${CYAN}./scripts/dev/start_all.sh${NC}"
echo ""
