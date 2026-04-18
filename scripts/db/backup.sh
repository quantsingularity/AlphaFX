#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Database Backup
# Creates a timestamped PostgreSQL dump.
# Works with Docker Compose or a direct pg_dump connection.
#
# Usage:
#   ./scripts/db/backup.sh                      # Docker Compose mode
#   ./scripts/db/backup.sh --local              # local pg_dump using .env vars
#   ./scripts/db/backup.sh --output /backups    # custom output directory
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

MODE="docker"
OUTPUT_DIR="$ROOT_DIR/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="alphafx_backup_${TIMESTAMP}.sql"

for arg in "$@"; do
    case $arg in
        --local)   MODE="local" ;;
        --output)  shift; OUTPUT_DIR="$1" ;;
    esac
done

log()  { echo -e "${CYAN}[backup]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC}     $1"; }
die()  { echo -e "${RED}[error]${NC}  $1"; exit 1; }

mkdir -p "$OUTPUT_DIR"
BACKUP_PATH="$OUTPUT_DIR/$FILENAME"

# -----------------------------------------------------------------------------
# Load .env variables
# -----------------------------------------------------------------------------

if [ -f "$ROOT_DIR/.env" ]; then
    # Export only DB-related vars safely
    DB_PASSWORD=$(grep '^DB_PASSWORD=' "$ROOT_DIR/.env" | cut -d'=' -f2- | tr -d '"' || echo "alphafx_secret")
    DATABASE_URL=$(grep '^DATABASE_URL=' "$ROOT_DIR/.env" | cut -d'=' -f2- | tr -d '"' || echo "")
else
    DB_PASSWORD="alphafx_secret"
    DATABASE_URL=""
fi

# -----------------------------------------------------------------------------
# Run backup
# -----------------------------------------------------------------------------

if [ "$MODE" = "docker" ]; then
    log "Backing up via Docker Compose (container: db)..."
    docker compose exec -T db pg_dump \
        -U alphafx \
        -d alphafx \
        --no-password \
        --format=plain \
        --no-owner \
        --no-acl \
        > "$BACKUP_PATH" \
        || die "pg_dump failed. Is the db container running?"

elif [ "$MODE" = "local" ]; then
    command -v pg_dump >/dev/null 2>&1 || die "pg_dump not found. Install PostgreSQL client tools."

    if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == postgresql* ]]; then
        log "Backing up via local pg_dump using DATABASE_URL..."
        PGPASSWORD="$DB_PASSWORD" pg_dump \
            "$DATABASE_URL" \
            --no-password \
            --format=plain \
            --no-owner \
            --no-acl \
            > "$BACKUP_PATH" \
            || die "pg_dump failed. Check DATABASE_URL in .env"
    else
        die "DATABASE_URL not set or not PostgreSQL. Set it in .env for local backup."
    fi
fi

# Compress
gzip "$BACKUP_PATH"
FINAL_PATH="${BACKUP_PATH}.gz"

FILESIZE=$(du -sh "$FINAL_PATH" | cut -f1)
ok "Backup saved: $FINAL_PATH ($FILESIZE)"

# -----------------------------------------------------------------------------
# Retention: keep only last 10 backups
# -----------------------------------------------------------------------------

BACKUP_COUNT=$(ls "$OUTPUT_DIR"/alphafx_backup_*.sql.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
    log "Pruning old backups (keeping last 10)..."
    ls -t "$OUTPUT_DIR"/alphafx_backup_*.sql.gz | tail -n +11 | xargs rm -f
    ok "Old backups pruned"
fi
