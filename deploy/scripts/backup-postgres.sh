#!/usr/bin/env bash
set -euo pipefail

: "${HADIR_DATABASE_URL:?Set HADIR_DATABASE_URL to a libpq PostgreSQL URL}"
: "${HADIR_BACKUP_DIR:=/var/backups/hadir}"

install -d -m 0700 "$HADIR_BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="$HADIR_BACKUP_DIR/hadir-$timestamp.dump"

pg_dump --format=custom --compress=9 --no-owner --no-privileges \
  --dbname="$HADIR_DATABASE_URL" --file="$archive"
pg_restore --list "$archive" >/dev/null
sha256sum "$archive" >"$archive.sha256"
find "$HADIR_BACKUP_DIR" -type f -name 'hadir-*.dump*' -mtime +30 -delete
printf 'Backup verified: %s\n' "$archive"
