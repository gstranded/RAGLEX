#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/law_backend_flask"
FRONTEND_DIR="${ROOT_DIR}/law_front"

ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.local}"
if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
  set +a
fi

VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/.run}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/.logs}"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-5000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-13000}"

normalize_sqlite_url() {
  local url="$1"

  case "${url}" in
    sqlite:///:memory: | sqlite:////*)
      printf '%s\n' "${url}"
      return 0
      ;;
    sqlite:///*)
      local relative_path="${url#sqlite:///}"
      printf 'sqlite:///%s/%s\n' "${ROOT_DIR}" "${relative_path}"
      return 0
      ;;
    *)
      printf '%s\n' "${url}"
      return 0
      ;;
  esac
}

ensure_sqlite_parent_dir() {
  local url="$1"

  case "${url}" in
    sqlite:///:memory:)
      return 0
      ;;
    sqlite:///*)
      local db_path="${url#sqlite:///}"
      mkdir -p "$(dirname "${db_path}")"
      return 0
      ;;
    *)
      return 0
      ;;
  esac
}

if [ -n "${DEV_DATABASE_URL:-}" ]; then
  DEV_DATABASE_URL="$(normalize_sqlite_url "${DEV_DATABASE_URL}")"
  ensure_sqlite_parent_dir "${DEV_DATABASE_URL}"
  export DEV_DATABASE_URL
fi

if [ -n "${DATABASE_URL:-}" ]; then
  DATABASE_URL="$(normalize_sqlite_url "${DATABASE_URL}")"
  ensure_sqlite_parent_dir "${DATABASE_URL}"
  export DATABASE_URL
fi

mkdir -p "${RUN_DIR}" "${LOG_DIR}" "${BACKEND_DIR}/data"

export ROOT_DIR BACKEND_DIR FRONTEND_DIR RUN_DIR LOG_DIR VENV_DIR
export BACKEND_HOST BACKEND_PORT FRONTEND_HOST FRONTEND_PORT
