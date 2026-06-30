#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"

if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    key="$(printf '%s' "$key" | xargs)"
    [[ -z "$key" ]] && continue
    export "$key=$value"
  done < "$ENV_FILE"
else
  echo "Aviso: $ENV_FILE nao existe. O Docker Compose usara apenas variaveis exportadas no ambiente."
fi

required=(
  JWT_SECRET_KEY
  ADMIN_BOOTSTRAP_EMAIL
  ADMIN_BOOTSTRAP_PASSWORD
  SYSTEM_ADMIN_EMAILS
  CORS_ALLOWED_ORIGINS
  CORS_ALLOWED_ORIGIN_REGEX
)

recommended=(
  CGU_API_KEY
  PORTAL_TRANSPARENCIA_API_KEY
  OPENAI_API_KEY
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
)

missing_required=()
for name in "${required[@]}"; do
  value="${!name:-}"
  if [[ -z "$value" ]]; then
    missing_required+=("$name")
  fi
done

missing_recommended=()
for name in "${recommended[@]}"; do
  value="${!name:-}"
  if [[ -z "$value" ]]; then
    missing_recommended+=("$name")
  fi
done

if (( ${#missing_required[@]} > 0 )); then
  echo "Aviso: variaveis obrigatorias ausentes para admin/login: ${missing_required[*]}" >&2
  echo "Configure estes nomes como Codespaces Secrets ou crie um .env local gitignored antes de subir o Docker." >&2
  exit 1
fi

if (( ${#missing_recommended[@]} > 0 )); then
  echo "Aviso: variaveis recomendadas ausentes para integracoes reais: ${missing_recommended[*]}" >&2
fi

if [[ "${JWT_SECRET_KEY:-}" == "ongp-change-me-in-production" || "${JWT_SECRET_KEY:-}" == "ongp-local-dev-secret-change-me" ]]; then
  echo "Aviso: JWT_SECRET_KEY esta usando valor padrao. Gere uma chave forte em Secrets." >&2
fi

if (( ${#missing_required[@]} == 0 )); then
  echo "Secrets essenciais de runtime encontrados."
fi
