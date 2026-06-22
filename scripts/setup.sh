#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

min_version() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null
}

PYTHON=""
for candidate in python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && min_version "$candidate"; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "ERROR: CDSS requires Python 3.11 or newer." >&2
  echo "Install Python 3.11+ (e.g. from python.org) and rerun: make setup" >&2
  exit 1
fi

echo "Using $($PYTHON --version) at $(command -v "$PYTHON")"

if [[ ! -d .venv ]] || ! .venv/bin/python -c 'import sys; assert sys.version_info >= (3, 11)' 2>/dev/null; then
  echo "Creating virtual environment in .venv ..."
  rm -rf .venv
  "$PYTHON" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo ""
echo "Setup complete. Run the app with: ./run  or  make run"
