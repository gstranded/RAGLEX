#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

show_process() {
  local name="$1"
  local pid_file="$2"

  if [ ! -f "${pid_file}" ]; then
    echo "[status] ${name}: not started"
    return
  fi

  local pid
  pid="$(cat "${pid_file}")"
  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[status] ${name}: running (pid=${pid})"
  else
    echo "[status] ${name}: stale pid file (pid=${pid})"
  fi
}

show_process backend "${RUN_DIR}/backend.pid"
show_process frontend "${RUN_DIR}/frontend.pid"

echo "[status] backend health:"
curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/health" || true
echo
