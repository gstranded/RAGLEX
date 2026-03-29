#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

STARTED_LOCAL="false"
BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/api/health"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"
TEST_BASE_URL="${BACKEND_URL}"

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
  echo "[regression] backend already healthy: ${BACKEND_HEALTH_URL}"
else
  echo "== start local services =="
  STARTED_LOCAL="true"
  "${ROOT_DIR}/scripts/start_local.sh"
fi

echo "== backend health =="
curl -fsS "${BACKEND_HEALTH_URL}"
echo

if curl -fsS "${FRONTEND_URL}" >/dev/null 2>&1; then
  TEST_BASE_URL="${FRONTEND_URL}"
  echo "== frontend health =="
  curl -fsS "${FRONTEND_URL}" >/dev/null
  echo "[regression] frontend reachable: ${FRONTEND_URL}"
else
  echo "[regression] frontend dev server not detected at ${FRONTEND_URL}; falling back to backend base URL"
fi

echo "== frontend production build =="
(cd "${FRONTEND_DIR}" && npm run build)

echo "== full regression =="
RAGLEX_BASE_URL="${TEST_BASE_URL}" \
  "${VENV_DIR}/bin/python" "${ROOT_DIR}/scripts/e2e_full.py"

echo "[regression] OK"
