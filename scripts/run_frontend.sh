#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

if ! command -v npm >/dev/null 2>&1; then
  echo "[frontend] ERROR: npm not found" >&2
  exit 2
fi

cd "${FRONTEND_DIR}"

if [ ! -d node_modules ] || [ "${FORCE_NPM_INSTALL:-false}" = "true" ]; then
  echo "[frontend] Installing npm dependencies..."
  npm install
fi

export VITE_PROXY_TARGET="${VITE_PROXY_TARGET:-http://127.0.0.1:${BACKEND_PORT}}"
export VITE_DEV_PORT="${FRONTEND_PORT}"
export FRONTEND_PORT

HOST="${HOST:-$FRONTEND_HOST}"
PORT="${PORT:-$FRONTEND_PORT}"

echo "[frontend] VITE_PROXY_TARGET=${VITE_PROXY_TARGET}"
echo "[frontend] Starting http://${HOST}:${PORT}"

exec npm run serve -- --host "${HOST}" --port "${PORT}"
