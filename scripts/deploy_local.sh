#!/usr/bin/env bash
# Despliega el sistema completo en local con un solo comando (modo demo,
# sin credenciales externas): crea/reutiliza el venv, instala dependencias,
# libera el puerto, levanta el servidor en background, espera a que esté
# saludable y muestra la clave de desarrollo + las URLs listas para usar.
#
# Uso:
#   ./scripts/deploy_local.sh          # modo demo (LLM_PROVIDER=mock)
#   PORT=8001 ./scripts/deploy_local.sh
#   ./scripts/deploy_local.sh --stop   # detiene el servidor levantado por este script
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-8000}"
VENV_DIR=".venv"
DATA_DIR="backend/data"
LOG_FILE="$DATA_DIR/server.out"
PID_FILE="$DATA_DIR/server.pid"

mkdir -p "$DATA_DIR"

stop() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    kill "$(cat "$PID_FILE")"
    echo "🛑 Servidor (PID $(cat "$PID_FILE")) detenido."
  else
    echo "ℹ️  No hay un servidor en ejecución (según $PID_FILE)."
  fi
  lsof -ti:"$PORT" -sTCP:LISTEN 2>/dev/null | xargs -r kill 2>/dev/null || true
  rm -f "$PID_FILE"
}

if [ "${1:-}" = "--stop" ]; then
  stop
  exit 0
fi

echo "🔧 Preparando entorno (venv + dependencias)..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -q -r requirements.txt

echo "🧹 Liberando el puerto $PORT si está ocupado..."
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  kill "$(cat "$PID_FILE")" 2>/dev/null || true
fi
lsof -ti:"$PORT" -sTCP:LISTEN 2>/dev/null | xargs -r kill 2>/dev/null || true
sleep 1

export LLM_PROVIDER="${LLM_PROVIDER:-mock}"
export APP_ENV="${APP_ENV:-development}"
export PORT

echo "🚀 Iniciando servidor (LLM=$LLM_PROVIDER, APP_ENV=$APP_ENV, puerto=$PORT)..."
nohup "$VENV_DIR/bin/python3" -m backend.server > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
disown

echo "⏳ Esperando a que el servidor esté saludable..."
ready=false
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done

if [ "$ready" != "true" ]; then
  echo "❌ El servidor no respondió a tiempo. Revisa $LOG_FILE"
  tail -n 30 "$LOG_FILE" || true
  exit 1
fi

# Fuerza la generación (lazy) de la clave admin de desarrollo, si aplica,
# haciendo una petición autenticada con una credencial dummy.
if [ -z "${API_KEYS:-}" ]; then
  curl -s -o /dev/null -X POST "http://localhost:$PORT/api/chat" \
    -H "X-API-Key: probe" -H "Content-Type: application/json" \
    -d '{"message":"probe"}' || true
  sleep 1
  DEV_KEY=$(grep -o 'clave de desarrollo = .*' "$LOG_FILE" | tail -1 | awk '{print $NF}')
fi

echo ""
echo "✅ Sistema desplegado (PID $SERVER_PID)"
echo "   API:        http://localhost:$PORT/api/health"
echo "   Dashboard:  http://localhost:$PORT/dashboard/"
echo "   Frontend:   abre frontend/index.html en tu navegador"
echo "   OpenAI-compat: http://localhost:$PORT/v1/chat/completions"
if [ -n "${DEV_KEY:-}" ]; then
  echo "   Clave admin (dev, un solo uso): $DEV_KEY"
  echo ""
  echo "   Ejemplo:"
  echo "   curl -X POST http://localhost:$PORT/api/chat \\"
  echo "     -H \"X-API-Key: $DEV_KEY\" -H \"Content-Type: application/json\" \\"
  echo "     -d '{\"message\": \"No puedo entrar al CRM\"}'"
fi
echo ""
echo "   Logs:    tail -f $LOG_FILE"
echo "   Detener: ./scripts/deploy_local.sh --stop"
