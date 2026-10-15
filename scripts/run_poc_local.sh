#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.poc}"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.poc.yml)

if [[ ! -f "$ENV_FILE" ]]; then
  echo "No existe $ENV_FILE. Copie .env.poc.example y complete sus valores." >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

required=(
  API_KEYS CORS_ORIGINS
  SERVICETONIC_BASE_URL SERVICETONIC_PROJECT_ID SERVICETONIC_USERNAME
  SERVICETONIC_PASSWORD SERVICETONIC_TEAM SERVICETONIC_FIELD_MAP
  POC_MANAGER_NAME POC_MANAGER_EMAIL
  TEAMS_BOT_APP_ID TEAMS_BOT_APP_PASSWORD TEAMS_TENANT_ID PUBLIC_BASE_URL
)
for name in "${required[@]}"; do
  value="${!name:-}"
  if [[ -z "$value" || "$value" == *"CHANGE_ME"* ]]; then
    echo "Falta configurar $name en $ENV_FILE" >&2
    exit 2
  fi
done

case "${1:-up}" in
  up)
    "${COMPOSE[@]}" up --build -d
    echo "PoC disponible en http://localhost:${PORT:-8000}"
    echo "Configure Teams Bot messaging endpoint: ${PUBLIC_BASE_URL%/}/api/teams/messages"
    ;;
  down) "${COMPOSE[@]}" down ;;
  logs) "${COMPOSE[@]}" logs -f api ;;
  *) echo "Uso: $0 [up|down|logs]" >&2; exit 2 ;;
esac
