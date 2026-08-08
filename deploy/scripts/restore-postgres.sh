#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /secure/path/hadir-TIMESTAMP.dump" >&2
  exit 2
fi
: "${HADIR_RESTORE_DATABASE_URL:?Set HADIR_RESTORE_DATABASE_URL to an empty validation database}"

archive="$1"
test -f "$archive"
if [[ -f "$archive.sha256" ]]; then
  sha256sum --check "$archive.sha256"
fi
pg_restore --list "$archive" >/dev/null
pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges \
  --dbname="$HADIR_RESTORE_DATABASE_URL" "$archive"
printf 'Restore completed into the explicitly configured validation database.\n'
