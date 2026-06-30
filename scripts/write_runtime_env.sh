#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---if-missing}"
ENV_FILE="${ENV_FILE:-.env}"

if [[ "$MODE" != "--if-missing" && "$MODE" != "--force" ]]; then
  echo "Uso: bash scripts/write_runtime_env.sh [--if-missing|--force]" >&2
  exit 2
fi

if [[ "$MODE" == "--if-missing" && -f "$ENV_FILE" ]]; then
  echo "$ENV_FILE ja existe. Mantendo arquivo local gitignored."
  exit 0
fi

tmp_file="$(mktemp)"
cleanup() {
  rm -f "$tmp_file"
}
trap cleanup EXIT

write_var() {
  local name="$1"
  local default_value="${2:-}"
  local value="${!name:-$default_value}"
  printf '%s=%s\n' "$name" "$value" >> "$tmp_file"
}

write_var POSTGRES_DB "ongp"
write_var POSTGRES_USER "ongp_user"
write_var POSTGRES_PASSWORD "ongp_password"
write_var POSTGRES_HOST "localhost"
write_var POSTGRES_PORT "5432"
write_var DB_URL "postgresql+psycopg://ongp_user:ongp_password@localhost:5432/ongp"
write_var DATABASE_URL "postgresql+psycopg://ongp_user:ongp_password@localhost:5432/ongp"
write_var REDIS_URL "redis://localhost:6379/0"
write_var NEO4J_URI "bolt://localhost:7687"
write_var NEO4J_USER "neo4j"
write_var NEO4J_PASSWORD "ongp_password"
write_var NEO4J_DATABASE "neo4j"
write_var ELASTICSEARCH_URL "http://localhost:9200"
write_var HTTP_VERIFY_SSL "true"
write_var CGU_API_KEY
write_var PORTAL_TRANSPARENCIA_API_KEY "${CGU_API_KEY:-}"
write_var JWT_SECRET_KEY
write_var JWT_ALGORITHM "HS256"
write_var JWT_EXPIRE_MINUTES "60"
write_var AUTH_COOKIE_NAME "ongp_token"
write_var AUTH_COOKIE_SECURE "true"
write_var AUTH_COOKIE_SAMESITE "lax"
write_var AUTH_COOKIE_DOMAIN
write_var SYSTEM_ADMIN_EMAILS
write_var ADMIN_BOOTSTRAP_EMAIL
write_var ADMIN_BOOTSTRAP_PASSWORD
write_var ADMIN_BOOTSTRAP_RESET_PASSWORD "true"
write_var CORS_ALLOWED_ORIGINS "http://localhost:3000,http://127.0.0.1:3000,https://localhost:3000,https://127.0.0.1:3000"
write_var CORS_ALLOWED_ORIGIN_REGEX "https://.*\\.(app\\.github\\.dev|github\\.dev|githubpreview\\.dev)"
write_var TRUSTED_HOSTS "localhost,127.0.0.1,testserver,api,ongp-api,web,ongp-web,*.github.dev,*.app.github.dev,*.githubpreview.dev"
write_var RATE_LIMIT_ENABLED "true"
write_var RATE_LIMIT_MAX_REQUESTS "240"
write_var RATE_LIMIT_WINDOW_SECONDS "60"
write_var RATE_LIMIT_BURST_MAX_REQUESTS "40"
write_var RATE_LIMIT_BURST_WINDOW_SECONDS "10"
write_var MAX_REQUEST_BODY_BYTES "2000000"
write_var SECURITY_HSTS_ENABLED "true"
write_var SECURITY_HSTS_MAX_AGE_SECONDS "31536000"
write_var OPENAI_API_KEY
write_var OPENAI_MODEL "gpt-4o-mini"
write_var GOOGLE_CLIENT_ID
write_var GOOGLE_CLIENT_SECRET
write_var GOOGLE_REDIRECT_URI "http://localhost:8000/api/v1/auth/oauth/google/callback"
write_var GOVBR_CLIENT_ID
write_var GOVBR_REDIRECT_URI "http://localhost:8000/api/v1/auth/oauth/govbr/callback"
write_var NEXT_PUBLIC_API_BASE_URL "/api/backend"
write_var INTERNAL_API_BASE_URL "http://localhost:8000/api/v1"

mv "$tmp_file" "$ENV_FILE"
chmod 600 "$ENV_FILE" 2>/dev/null || true
echo "$ENV_FILE gerado a partir das variaveis do ambiente. Nao commitar este arquivo."
