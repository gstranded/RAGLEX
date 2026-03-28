#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUN_DIR}/frontend.pid"
BACKEND_LOG_FILE="${LOG_DIR}/backend.log"
FRONTEND_LOG_FILE="${LOG_DIR}/frontend.log"

port_in_use() {
  local port="$1"
  ss -ltn "( sport = :${port} )" | awk 'NR > 1 { found = 1 } END { exit(found ? 0 : 1) }'
}

ensure_port_available() {
  local name="$1"
  local port="$2"

  if port_in_use "${port}"; then
    echo "[start] ERROR: ${name} port ${port} is already in use" >&2
    return 1
  fi
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local retries="${3:-60}"
  for _ in $(seq 1 "${retries}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "[start] ${label} is ready: ${url}"
      return 0
    fi
    sleep 1
  done
  echo "[start] ERROR: ${label} did not become ready: ${url}" >&2
  return 1
}

start_process() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"
  local port="$4"
  shift 4

  if [ -f "${pid_file}" ]; then
    local pid
    pid="$(cat "${pid_file}")"
    if kill -0 "${pid}" >/dev/null 2>&1; then
      echo "[start] ${name} already running (pid=${pid})"
      return 0
    fi
    rm -f "${pid_file}"
  fi

  ensure_port_available "${name}" "${port}"

  nohup "$@" >"${log_file}" 2>&1 &
  local pid=$!
  sleep 1
  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    rm -f "${pid_file}"
    echo "[start] ERROR: ${name} exited early, check ${log_file}" >&2
    return 1
  fi
  echo "${pid}" >"${pid_file}"
  echo "[start] ${name} started (pid=${pid}, log=${log_file})"
}

if [ ! -x "${VENV_DIR}/bin/python" ]; then
  echo "[start] Bootstrapping Python environment..."
  "${ROOT_DIR}/scripts/bootstrap_python.sh"
fi

if [ ! -d "${FRONTEND_DIR}/node_modules" ] || [ "${FORCE_NPM_INSTALL:-false}" = "true" ]; then
  echo "[start] Installing frontend dependencies..."
  (cd "${FRONTEND_DIR}" && npm install)
fi

start_process backend "${BACKEND_PID_FILE}" "${BACKEND_LOG_FILE}" "${BACKEND_PORT}" "${ROOT_DIR}/scripts/run_backend_sqlite.sh"
wait_for_url "http://127.0.0.1:${BACKEND_PORT}/api/health" "backend"

start_process frontend "${FRONTEND_PID_FILE}" "${FRONTEND_LOG_FILE}" "${FRONTEND_PORT}" "${ROOT_DIR}/scripts/run_frontend.sh"
wait_for_url "http://127.0.0.1:${FRONTEND_PORT}/" "frontend"

cat <<EOF
[start] RAGLEX is ready
- frontend: http://127.0.0.1:${FRONTEND_PORT}
- backend:  http://127.0.0.1:${BACKEND_PORT}
- health:   http://127.0.0.1:${BACKEND_PORT}/api/health
- logs:     ${LOG_DIR}
- pids:     ${RUN_DIR}
EOF
