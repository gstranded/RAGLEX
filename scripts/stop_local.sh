#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

stop_process() {
  local name="$1"
  local pid_file="$2"

  if [ ! -f "${pid_file}" ]; then
    echo "[stop] ${name}: no pid file"
    return 0
  fi

  local pid
  pid="$(cat "${pid_file}")"
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
    wait "${pid}" 2>/dev/null || true
    echo "[stop] ${name} stopped (pid=${pid})"
  else
    echo "[stop] ${name}: pid ${pid} not running"
  fi

  rm -f "${pid_file}"
}

stop_process backend "${RUN_DIR}/backend.pid"
stop_process frontend "${RUN_DIR}/frontend.pid"
