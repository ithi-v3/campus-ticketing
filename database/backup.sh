#!/usr/bin/env bash
# Logical backup of the ticketing database. Usage: ./backup.sh [database_url]
# Restore with:  pg_restore --clean --if-exists -d <database_url> <file>.dump
set -euo pipefail

DB_URL="${1:-${DATABASE_URL:?pass a database url or set DATABASE_URL}}"
OUT_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$OUT_DIR"

FILE="$OUT_DIR/ticketing_$(date +%Y%m%d_%H%M%S).dump"
pg_dump -Fc "$DB_URL" > "$FILE"
echo "wrote $FILE"

# keep the 14 newest dumps
ls -1t "$OUT_DIR"/ticketing_*.dump | tail -n +15 | xargs -r rm --
