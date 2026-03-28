#!/usr/bin/env bash
set -euo pipefail

# Bootstrap Python deps on hosts where system python3 has NO pip/venv.
# Strategy:
#   1) Install pip into *user site-packages* via get-pip.py (no sudo required)
#   2) Install virtualenv into user site-packages
#   3) Create repo-local venv (.venv/) using virtualenv (does not require python3-venv)
#   4) Install backend requirements into that venv

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

pick_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    echo "${PYTHON_BIN}"
    return 0
  fi

  for candidate in python3.10 python3.11 python3.12 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      echo "${candidate}"
      return 0
    fi
  done

  return 1
}

PYTHON_BIN="$(pick_python || true)"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "[bootstrap] ERROR: ${PYTHON_BIN} not found" >&2
  exit 2
fi

if [ -x "${VENV_DIR}/bin/python" ] && [ "${FORCE_RECREATE_VENV:-false}" != "true" ]; then
  echo "[bootstrap] Reusing existing venv: ${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"
  cat <<EOF
[bootstrap] OK
- python: $("${VENV_DIR}/bin/python" --version 2>&1)
- venv: ${VENV_DIR}
- backend deps refreshed
EOF
  exit 0
fi

if ! "${PYTHON_BIN}" -m pip --version >/dev/null 2>&1; then
  echo "[bootstrap] pip not found for ${PYTHON_BIN}; installing via get-pip.py (user install, no sudo)…"
  TMP_GET_PIP="$(mktemp /tmp/get-pip.XXXXXX.py)"
  curl -fsSL -o "${TMP_GET_PIP}" https://bootstrap.pypa.io/get-pip.py
  "${PYTHON_BIN}" "${TMP_GET_PIP}" --user
fi

# Ensure tooling exists (user site). We call pip via python -m pip to avoid PATH issues.
"${PYTHON_BIN}" -m pip install --user --upgrade pip
"${PYTHON_BIN}" -m pip install --user "virtualenv>=20.26.0"

# Create venv (repo-local)
"${PYTHON_BIN}" --version
"${PYTHON_BIN}" -m virtualenv "${VENV_DIR}"

# Install backend deps
"${VENV_DIR}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"

cat <<EOF
[bootstrap] OK
- venv: ${VENV_DIR}
- backend deps: ${BACKEND_DIR}/requirements.txt

Next:
  ./scripts/run_backend_sqlite.sh
EOF
