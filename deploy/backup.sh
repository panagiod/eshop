#!/bin/bash
# Nightly SQLite copy. Example cron (root):
#   15 3 * * * /opt/eshop/deploy/backup.sh
set -euo pipefail

SRC="${DATA_DIR:-/var/lib/eshop}/eshop.db"
DEST="${DATA_DIR:-/var/lib/eshop}/backups"
mkdir -p "$DEST"

if [ ! -f "$SRC" ]; then
  echo "No database at $SRC yet"
  exit 0
fi

stamp=$(date -u +%Y%m%dT%H%M%SZ)
sqlite3 "$SRC" ".backup '${DEST}/eshop-${stamp}.db'"
find "$DEST" -name 'eshop-*.db' -mtime +14 -delete
echo "Wrote ${DEST}/eshop-${stamp}.db"
