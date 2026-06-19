#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Database Restore
# Restores a backup created by scripts/db/backup.sh.
# WARNING: This drops and recreates the database. Use with caution.
#
# Usage:
#   ./scripts/db/restore.sh backups/alphafx_backup_20250101_120000.sql.gz
#   ./scripts/db/restore.sh --list     # show available backups
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="$ROOT_DIR/backups"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${CYAN}[restore]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}      $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}    $1"; }
die()  { echo -e "${RED}[error]${NC}   $1"; exit 1; }

# List mode
if [ "${1:-}" = "--list" ]; then
    echo "Available backups in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/alphafx_backup_*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 0
fi

BACKUP_FILE="${1:-}"
[ -z "$BACKUP_FILE" ] && die "Usage: $0 <backup_file.sql.gz>"
[ -f "$BACKUP_FILE" ] || die "Backup file not found: $BACKUP_FILE"

# Confirmation prompt
warn "This will DROP and RECREATE the alphafx database."
warn "All current data will be lost."
echo ""
read -r -p "Type 'yes' to confirm: " CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "Aborted."; exit 1; }

# -----------------------------------------------------------------------------
# Decompress if needed
# -----------------------------------------------------------------------------

WORK_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    log "Decompressing backup..."
    TMP_FILE=$(mktemp /tmp/alphafx_restore_XXXX.sql)
    gunzip -c "$BACKUP_FILE" > "$TMP_FILE"
    WORK_FILE="$TMP_FILE"
    CLEANUP_TMP=true
else
    CLEANUP_TMP=false
fi

# -----------------------------------------------------------------------------
# Restore via Docker Compose
# -----------------------------------------------------------------------------

log "Dropping and recreating database..."
docker compose exec -T db psql -U alphafx -c "DROP DATABASE IF EXISTS alphafx;" postgres
docker compose exec -T db psql -U alphafx -c "CREATE DATABASE alphafx;" postgres

log "Restoring from $BACKUP_FILE..."
docker compose exec -T db psql -U alphafx -d alphafx < "$WORK_FILE"

[ "$CLEANUP_TMP" = true ] && rm -f "$TMP_FILE"

# -----------------------------------------------------------------------------
# Run migrations to ensure schema is current
# -----------------------------------------------------------------------------

log "Running post-restore migrations..."
docker compose exec backend python manage.py migrate --noinput

ok "Database restore complete"
