#!/usr/bin/env bash
# Git Bash and other bash shells. On Windows, a missing Python is unpacked into .python.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

real_python() {
  local bin="$1"
  [[ -n "$bin" ]] || return 1
  case "$bin" in
    *WindowsApps*) return 1 ;;
  esac
  "$bin" -c "import sys, venv, ensurepip; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1
}

venv_python() {
  if [[ -f "$ROOT/.venv/Scripts/python.exe" ]]; then
    printf '%s\n' "$ROOT/.venv/Scripts/python.exe"
  elif [[ -f "$ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$ROOT/.venv/bin/python"
  fi
}

PY="$(venv_python || true)"
if [[ -z "$PY" ]]; then
  BASE=""
  py_bin="$(command -v py || true)"
  case "$py_bin" in
    ""|*WindowsApps*) ;;
    *)
      if py -3 -c "import sys, venv, ensurepip; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1; then
        BASE="py -3"
      fi
      ;;
  esac
  if [[ -z "$BASE" ]] && command -v python3 >/dev/null 2>&1 && real_python python3; then
    BASE="python3"
  fi
  if [[ -z "$BASE" ]] && command -v python >/dev/null 2>&1 && real_python python; then
    BASE="python"
  fi
  if [[ -z "$BASE" ]]; then
    if command -v powershell.exe >/dev/null 2>&1; then
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ROOT/install.ps1"
      exit $?
    fi
    echo "Python is not found." >&2
    exit 1
  fi
  # shellcheck disable=SC2086
  $BASE -m venv "$ROOT/.venv"
  PY="$(venv_python || true)"
fi

if [[ -z "$PY" || ! -f "$PY" ]]; then
  echo "Python is not found." >&2
  exit 1
fi

"$PY" -m pip install -U pip
"$PY" -m pip install -e "$ROOT"
"$PY" -m video_editor.install
