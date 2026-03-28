#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

if [ ! -x "${VENV_DIR}/bin/python" ]; then
  echo "[backend] ERROR: venv not found at ${VENV_DIR}. Run: ./scripts/bootstrap_python.sh" >&2
  exit 2
fi

mkdir -p "${BACKEND_DIR}/data"

# Minimal local mode:
# - SQLite (no MySQL)
# - MinIO disabled (avoid startup timeouts + missing local service)
export DEV_DATABASE_URL="${DEV_DATABASE_URL:-sqlite:///${BACKEND_DIR}/data/raglex-dev.sqlite3}"
export DATABASE_URL="${DATABASE_URL:-$DEV_DATABASE_URL}"
export MINIO_DISABLED="${MINIO_DISABLED:-true}"
export OPENAI_COMPAT_BASE_URL="${OPENAI_COMPAT_BASE_URL:-http://127.0.0.1:11434/v1}"
export OPENAI_COMPAT_API_KEY="${OPENAI_COMPAT_API_KEY:-ollama}"
export OPENAI_CHAT_MODEL="${OPENAI_CHAT_MODEL:-qwen2.5:7b}"

export FLASK_ENV="${FLASK_ENV:-development}"
export FLASK_DEBUG="${FLASK_DEBUG:-True}"

HOST="${HOST:-$BACKEND_HOST}"
PORT="${PORT:-$BACKEND_PORT}"

echo "[backend] Using DEV_DATABASE_URL=${DEV_DATABASE_URL}"
echo "[backend] MINIO_DISABLED=${MINIO_DISABLED}"
echo "[backend] LLM=${OPENAI_CHAT_MODEL} @ ${OPENAI_COMPAT_BASE_URL}"
echo "[backend] Starting http://${HOST}:${PORT} (health: /api/health)"

exec "${VENV_DIR}/bin/python" "${BACKEND_DIR}/run.py" --host "${HOST}" --port "${PORT}" --env development --debug
