#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# AlphaFX - Generate Django Secret Key
# Generates a cryptographically secure SECRET_KEY for Django.
# Optionally writes it directly into the .env file.
#
# Usage:
#   ./scripts/maintenance/generate_secret_key.sh
#   ./scripts/maintenance/generate_secret_key.sh --write   # update .env in place
# -----------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

WRITE=false
[ "${1:-}" = "--write" ] && WRITE=true

# Generate 50-character secret key using Django's own method
SECRET=$(python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits + '!@#\$%^&*(-_=+)'
print(''.join(secrets.choice(chars) for _ in range(50)))
")

if [ "$WRITE" = true ]; then
    ENV_FILE="$ROOT_DIR/.env"
    if [ -f "$ENV_FILE" ]; then
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" "$ENV_FILE"
        echo "SECRET_KEY updated in .env"
    else
        echo "SECRET_KEY=${SECRET}" >> "$ENV_FILE"
        echo "SECRET_KEY written to .env"
    fi
else
    echo ""
    echo "Generated SECRET_KEY:"
    echo ""
    echo "  SECRET_KEY=${SECRET}"
    echo ""
    echo "Add this to your .env file, or run with --write to update it automatically."
    echo ""
fi
