#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL is required}"
backup_dir="${PAYMENTOR_BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" --file="$backup_dir/paymentor-$stamp.dump"
find "$backup_dir" -type f -name 'paymentor-*.dump' -mtime +14 -delete
echo "$backup_dir/paymentor-$stamp.dump"
