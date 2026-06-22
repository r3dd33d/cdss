#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "No .venv found — running setup first ..."
  "$ROOT/scripts/setup.sh"
fi

exec "$VENV_PYTHON" -m streamlit run app/main.py "$@"
