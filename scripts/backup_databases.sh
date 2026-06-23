#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "${BACKUP_DIR}"

PG_HOST="${PG_HOST:-postgres}"
PG_PORT="${PG_PORT:-5432}"
PG_DATABASE="${PG_DATABASE:-ongp}"
PG_USER="${PG_USER:-ongp_user}"
export PGPASSWORD="${PGPASSWORD:-ongp_password}"

pg_dump \
  --host "${PG_HOST}" \
  --port "${PG_PORT}" \
  --username "${PG_USER}" \
  --dbname "${PG_DATABASE}" \
  --format custom \
  --file "${BACKUP_DIR}/ongp_postgres_${TIMESTAMP}.dump"

if command -v neo4j-admin >/dev/null 2>&1; then
  neo4j-admin database dump neo4j --to-path="${BACKUP_DIR}"
  mv "${BACKUP_DIR}/neo4j.dump" "${BACKUP_DIR}/ongp_neo4j_${TIMESTAMP}.dump"
fi
