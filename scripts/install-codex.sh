#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${CHIBI_REPO_URL:-git+https://github.com/soccz/chibi-mcp.git#subdirectory=server}"
MARKETPLACE="${CHIBI_MARKETPLACE:-soccz/chibi-mcp}"
MCP_NAME="${CHIBI_MCP_NAME:-chibi}"
PYTHON_BIN=""
PIPX_CMD=()

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

setup_python() {
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
  else
    echo "missing required command: python3 or python" >&2
    exit 1
  fi
}

setup_pipx() {
  if command -v pipx >/dev/null 2>&1; then
    PIPX_CMD=(pipx)
    return 0
  fi

  if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    echo "pipx not found; installing pipx with Homebrew" >&2
    brew install pipx
    if command -v pipx >/dev/null 2>&1; then
      PIPX_CMD=(pipx)
      return 0
    fi
  fi

  echo "pipx not found; installing pipx with $PYTHON_BIN -m pip" >&2
  "$PYTHON_BIN" -m pip install --user pipx
  PIPX_CMD=("$PYTHON_BIN" -m pipx)
}

pipx_run() {
  "${PIPX_CMD[@]}" "$@"
}

setup_python
setup_pipx
need codex

find_chibi_cmd() {
  if command -v chibi-mcp >/dev/null 2>&1; then
    command -v chibi-mcp
    return 0
  fi

  local pipx_bin
  pipx_bin="$(pipx_run environment --value PIPX_BIN_DIR 2>/dev/null || true)"

  local user_base
  user_base="$("$PYTHON_BIN" -m site --user-base 2>/dev/null || true)"

  for candidate in \
    "$pipx_bin/chibi-mcp" \
    "$HOME/.local/bin/chibi-mcp" \
    "$user_base/bin/chibi-mcp"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  echo "chibi-mcp was installed, but the executable was not found on PATH." >&2
  echo "Run: pipx ensurepath" >&2
  exit 1
}

check_reports_tkinter() {
  local check_output="$1"
  printf '%s' "$check_output" | "$PYTHON_BIN" -c '
import json
import sys

try:
    report = json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if report.get("tkinter") else 1)
'
}

homebrew_tk_formula() {
  local python_minor
  python_minor="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  if [ -n "$python_minor" ]; then
    printf 'python-tk@%s\n' "$python_minor"
  else
    printf 'python-tk\n'
  fi
}

print_tkinter_help() {
  local brew_formula
  brew_formula="$(homebrew_tk_formula)"

  echo "warning: Python tkinter is unavailable; MCP tools can run, but the floating pet window cannot open." >&2
  echo "macOS Homebrew Python: brew install $brew_formula" >&2
  echo "Ubuntu/Debian system Python: sudo apt-get install -y python3-tk" >&2
  echo "After installing Tk, run: pipx reinstall chibi-mcp" >&2
}

repair_tkinter_if_possible() {
  local brew_formula

  print_tkinter_help
  if [ "${CHIBI_SKIP_TK_REPAIR:-0}" = "1" ]; then
    return 1
  fi

  if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    brew_formula="$(homebrew_tk_formula)"
    echo "Attempting macOS Tk repair: brew install $brew_formula" >&2
    if brew install "$brew_formula" || { [ "$brew_formula" != "python-tk" ] && brew install python-tk; }; then
      echo "Reinstalling chibi-mcp so the pipx venv picks up tkinter..." >&2
      pipx_run reinstall chibi-mcp || pipx_run install --force "$REPO_URL"
      return 0
    fi
  fi

  if [ "${CHIBI_AUTO_INSTALL_TK:-0}" = "1" ] && command -v apt-get >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1; then
    echo "Attempting Linux Tk repair: sudo apt-get install -y python3-tk" >&2
    sudo apt-get update
    sudo apt-get install -y python3-tk
    pipx_run reinstall chibi-mcp || pipx_run install --force "$REPO_URL"
    return 0
  fi

  return 1
}

install_or_upgrade_server() {
  if pipx_run list --short 2>/dev/null | awk '{print $1}' | grep -qx "chibi-mcp"; then
    pipx_run upgrade chibi-mcp || pipx_run reinstall chibi-mcp
  else
    pipx_run install "$REPO_URL"
  fi
  pipx_run ensurepath >/dev/null 2>&1 || true
}

run_check_and_repair() {
  local check_output

  CHIBI_CMD="$(find_chibi_cmd)"
  if ! check_output="$("$CHIBI_CMD" --check 2>&1)"; then
    printf '%s\n' "$check_output" >&2
    echo "chibi-mcp installed, but the health check failed." >&2
    exit 1
  fi
  printf '%s\n' "$check_output"

  if ! check_reports_tkinter "$check_output" && repair_tkinter_if_possible "$check_output"; then
    CHIBI_CMD="$(find_chibi_cmd)"
    check_output="$("$CHIBI_CMD" --check)"
    printf '%s\n' "$check_output"
  fi
}

install_or_upgrade_server
run_check_and_repair

if codex mcp get "$MCP_NAME" >/dev/null 2>&1; then
  echo "Codex MCP '$MCP_NAME' already exists."
else
  codex mcp add "$MCP_NAME" -- "$CHIBI_CMD"
fi

codex plugin marketplace add "$MARKETPLACE" || true

echo "Codex install complete. Try: chibi 보여줘"
