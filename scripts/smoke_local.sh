#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== backend (python) =="
./scripts/bootstrap_python.sh

PORT="${PORT:-5000}"
export PORT

LOG="$(mktemp)"
(
  ./scripts/run_backend_sqlite.sh >"${LOG}" 2>&1 &
  PID=$!

  for i in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  echo "[smoke] /api/health:";
  curl -fsS "http://127.0.0.1:${PORT}/api/health"; echo

  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
)

echo "--- backend log tail ---"
tail -n 80 "${LOG}" || true

echo "== frontend (node) =="
(
  cd "${ROOT_DIR}/law_front"
  # Clean install to avoid reusing any existing node_modules (if present).
  rm -rf node_modules
  npm install
  npm run build
)

echo "[smoke] OK"
