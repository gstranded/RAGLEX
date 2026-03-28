#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cat <<'EOF'
== RAGLEX one-click local deploy ==

This script performs a local development deployment:
1. bootstrap Python dependencies
2. install frontend dependencies when needed
3. start backend and frontend

For a full verification after startup, run:
  ./scripts/smoke_local.sh
EOF

"${ROOT_DIR}/scripts/start_local.sh"
