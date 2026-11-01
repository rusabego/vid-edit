#!/usr/bin/env bash
# Git Bash and other bash shells. On Windows this creates .venv and registers the clients.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/Scripts/python.exe" && ! -x "$ROOT/.venv/bin/python" ]]; then
  if command -v py >/dev/null 2>&1; then
    py -3 -m venv "$ROOT/.venv"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$ROOT/.venv"
  elif command -v python >/dev/null 2>&1; then
    python -m venv "$ROOT/.venv"
  else
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ROOT/install.ps1"
    exit $?
  fi
fi

if [[ -x "$ROOT/.venv/Scripts/python.exe" ]]; then
  PY="$ROOT/.venv/Scripts/python.exe"
else
  PY="$ROOT/.venv/bin/python"
fi

"$PY" -m pip install -U pip
"$PY" -m pip install -e "$ROOT"
"$PY" -m video_editor.install
