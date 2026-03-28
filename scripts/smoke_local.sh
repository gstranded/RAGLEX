#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

STARTED_LOCAL="false"
BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/api/health"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}/"

cleanup() {
  if [ "${STARTED_LOCAL}" = "true" ]; then
    "${ROOT_DIR}/scripts/stop_local.sh" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

echo "== bootstrap =="
"${ROOT_DIR}/scripts/bootstrap_python.sh"

if curl -fsS "${BACKEND_HEALTH_URL}" >/dev/null 2>&1; then
  echo "== reuse running backend =="
  echo "[smoke] backend already healthy: ${BACKEND_HEALTH_URL}"
  if curl -fsS "${FRONTEND_URL}" >/dev/null 2>&1; then
    echo "[smoke] frontend already reachable: ${FRONTEND_URL}"
  else
    echo "[smoke] frontend dev server not detected at ${FRONTEND_URL}; continuing with backend smoke + production build"
  fi
else
  echo "== start local services =="
  STARTED_LOCAL="true"
  "${ROOT_DIR}/scripts/start_local.sh"
fi

echo "== backend health =="
curl -fsS "${BACKEND_HEALTH_URL}"
echo

echo "== frontend production build =="
(cd "${FRONTEND_DIR}" && npm run build)

echo "== end-to-end smoke =="
RAGLEX_BASE_URL="http://127.0.0.1:${BACKEND_PORT}" \
  "${VENV_DIR}/bin/python" "${ROOT_DIR}/scripts/e2e_smoke.py"

echo "[smoke] OK"
