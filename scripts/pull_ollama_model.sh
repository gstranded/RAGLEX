#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common_env.sh"

MODEL="${OLLAMA_MODEL:-${OPENAI_CHAT_MODEL:-qwen2.5:7b}}"

if ! command -v ollama >/dev/null 2>&1; then
  cat <<EOF >&2
[ollama] ERROR: ollama command not found.

Install Ollama first:
  https://ollama.com/download

Then run:
  ollama serve
  ./scripts/pull_ollama_model.sh
EOF
  exit 2
fi

echo "[ollama] pulling model: ${MODEL}"
ollama pull "${MODEL}"

cat <<EOF
[ollama] model ready
- model: ${MODEL}
- endpoint: http://127.0.0.1:11434/v1

Recommended .env.local values:
OPENAI_COMPAT_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_COMPAT_API_KEY=ollama
OPENAI_CHAT_MODEL=${MODEL}
EOF
