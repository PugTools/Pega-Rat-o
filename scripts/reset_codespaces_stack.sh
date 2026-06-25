#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-app}"

if [[ "$MODE" != "app" && "$MODE" != "full" ]]; then
  echo "Uso: bash scripts/reset_codespaces_stack.sh [app|full]" >&2
  exit 2
fi

echo "Parando containers do ONGP..."
docker compose --profile analytics --profile monitoring down --remove-orphans || true

echo "Removendo containers ONGP que ficaram orfaos..."
docker rm -f \
  ongp-api \
  ongp-web \
  ongp-celery-worker \
  ongp-postgres \
  ongp-redis \
  ongp-neo4j \
  ongp-elasticsearch \
  ongp-prometheus \
  ongp-grafana \
  >/dev/null 2>&1 || true

echo "Limpando redes Docker nao utilizadas..."
docker network prune -f >/dev/null || true

if [[ "$MODE" == "full" ]]; then
  echo "Subindo ONGP completo com analytics e monitoring..."
  docker compose --profile analytics --profile monitoring up -d --build --remove-orphans
else
  echo "Subindo ONGP essencial..."
  docker compose up -d --build --remove-orphans
fi

echo
docker compose --profile analytics --profile monitoring ps
