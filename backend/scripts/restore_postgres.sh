#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL is required}"
backup_file="${1:?Pass the .dump backup path as the first argument}"
pg_restore --clean --if-exists --no-owner --no-acl --dbname="$DATABASE_URL" "$backup_file"
