#!/usr/bin/env bash
# Empaqueta la app de Teams (teams-app/) en un .zip para que el administrador
# de Microsoft 365 la cargue en el Teams Admin Center (Fase 2, I7.b).
#
# Uso:
#   TEAMS_BOT_APP_ID=<guid> TEAMS_APP_DEVELOPER="Mi Empresa" \
#   TEAMS_APP_WEBSITE=https://helpdesk.ejemplo.com ./scripts/package_teams_app.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/teams-app"
OUT="$ROOT/dist/teams-app.zip"

: "${TEAMS_BOT_APP_ID:?Falta TEAMS_BOT_APP_ID (App ID del bot en Entra ID)}"
: "${TEAMS_APP_DEVELOPER:?Falta TEAMS_APP_DEVELOPER (nombre de la organizacion)}"
: "${TEAMS_APP_WEBSITE:?Falta TEAMS_APP_WEBSITE (https://...)}"
export TEAMS_BOT_APP_ID TEAMS_APP_DEVELOPER TEAMS_APP_WEBSITE

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

python3 - "$SRC/manifest.template.json" "$WORK/manifest.json" <<'PY'
import json, os, re, sys
src, dst = sys.argv[1], sys.argv[2]
# solo ${VAR}: "$schema" del manifiesto no es una variable
text = re.sub(r"\$\{(\w+)\}", lambda m: os.environ[m.group(1)], open(src, encoding="utf-8").read())
json.loads(text)  # falla si el resultado no es JSON valido
open(dst, "w", encoding="utf-8").write(text)
PY
cp "$SRC/color.png" "$SRC/outline.png" "$WORK/"

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$WORK" && zip -q "$OUT" manifest.json color.png outline.png)
echo "Paquete listo: $OUT"
