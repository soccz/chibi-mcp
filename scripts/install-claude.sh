#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${CHIBI_REPO_URL:-git+https://github.com/soccz/chibi-mcp.git#subdirectory=server}"
MARKETPLACE="${CHIBI_MARKETPLACE:-soccz/chibi-mcp}"
MCP_NAME="${CHIBI_MCP_NAME:-chibi}"
EXPECTED_VERSION="${CHIBI_EXPECT_VERSION:-1.4.28}"
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

claude_run() {
  if command -v timeout >/dev/null 2>&1; then
    timeout 45s claude "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout 45s claude "$@"
  else
    claude "$@"
  fi
}

run_privileged() {
  if [ "$(id -u 2>/dev/null || echo 1)" = "0" ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    return 1
  fi
}

setup_python
setup_pipx
need claude

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
  echo "Fedora/RHEL: sudo dnf install -y python3-tkinter" >&2
  echo "Arch: sudo pacman -S --noconfirm tk" >&2
  echo "openSUSE: sudo zypper --non-interactive install python3-tk" >&2
  echo "After installing Tk, rerun this installer or run: pipx uninstall chibi-mcp || true; pipx install \"$REPO_URL\"" >&2
}

repair_linux_tkinter() {
  if [ "$(uname -s)" != "Linux" ]; then
    return 1
  fi

  if command -v apt-get >/dev/null 2>&1; then
    run_privileged apt-get update && run_privileged apt-get install -y python3-tk
  elif command -v dnf >/dev/null 2>&1; then
    run_privileged dnf install -y python3-tkinter
  elif command -v yum >/dev/null 2>&1; then
    run_privileged yum install -y python3-tkinter
  elif command -v pacman >/dev/null 2>&1; then
    run_privileged pacman -Sy --noconfirm tk
  elif command -v zypper >/dev/null 2>&1; then
    run_privileged zypper --non-interactive install python3-tk
  elif command -v apk >/dev/null 2>&1; then
    run_privileged apk add py3-tkinter
  else
    return 1
  fi
}

install_server_from_github() {
  pipx_run uninstall chibi-mcp >/dev/null 2>&1 || true
  pipx_run install "$REPO_URL"
}

verify_installed_version() {
  local installed_version

  installed_version="$("$CHIBI_CMD" --version 2>/dev/null || true)"
  if [ "$installed_version" = "$EXPECTED_VERSION" ]; then
    return 0
  fi

  echo "warning: expected chibi-mcp $EXPECTED_VERSION but found ${installed_version:-unknown}; reinstalling fresh." >&2
  install_server_from_github
  CHIBI_CMD="$(find_chibi_cmd)"
  installed_version="$("$CHIBI_CMD" --version 2>/dev/null || true)"
  if [ "$installed_version" != "$EXPECTED_VERSION" ]; then
    echo "chibi-mcp version check failed: expected $EXPECTED_VERSION, got ${installed_version:-unknown}" >&2
    exit 1
  fi
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
      echo "Reinstalling chibi-mcp from GitHub so the pipx venv picks up tkinter..." >&2
      install_server_from_github
      return 0
    fi
  fi

  if [ "$(uname -s)" = "Linux" ]; then
    echo "Attempting Linux Tk repair with the detected package manager" >&2
    if repair_linux_tkinter; then
      install_server_from_github
      return 0
    fi
  fi

  if [ "${CHIBI_AUTO_INSTALL_TK:-0}" = "1" ] && command -v apt-get >/dev/null 2>&1; then
    echo "Attempting fallback Linux Tk repair: apt-get install -y python3-tk" >&2
    run_privileged apt-get update
    run_privileged apt-get install -y python3-tk
    install_server_from_github
    return 0
  fi

  return 1
}

install_or_upgrade_server() {
  echo "Installing chibi-mcp $EXPECTED_VERSION from GitHub..."
  install_server_from_github
  pipx_run ensurepath >/dev/null 2>&1 || true
}

run_check_and_repair() {
  local check_output

  CHIBI_CMD="$(find_chibi_cmd)"
  verify_installed_version
  if ! check_output="$("$CHIBI_CMD" --check 2>&1)"; then
    printf '%s\n' "$check_output" >&2
    echo "chibi-mcp installed, but the health check failed." >&2
    exit 1
  fi
  printf '%s\n' "$check_output"

  if ! check_reports_tkinter "$check_output" && repair_tkinter_if_possible "$check_output"; then
    CHIBI_CMD="$(find_chibi_cmd)"
    verify_installed_version
    check_output="$("$CHIBI_CMD" --check)"
    printf '%s\n' "$check_output"
  fi
}

sync_claude_plugin() {
  claude_run plugin marketplace add "$MARKETPLACE" >/dev/null 2>&1 || true

  if ! claude_run plugin marketplace update chibi-mcp >/dev/null 2>&1; then
    claude_run plugin marketplace update >/dev/null 2>&1 || true
  fi

  claude_run plugin uninstall --keep-data chibi >/dev/null 2>&1 || true

  if claude_run plugin install "chibi@chibi-mcp" >/dev/null 2>&1; then
    echo "Claude plugin 'chibi' installed/refreshed."
  elif claude_run plugin update chibi >/dev/null 2>&1; then
    echo "Claude plugin 'chibi' updated."
  else
    echo "warning: Claude plugin refresh failed; MCP registration is still complete." >&2
  fi
}

install_or_upgrade_server
run_check_and_repair

echo "Refreshing Claude MCP '$MCP_NAME' registration..."
claude_run mcp remove "$MCP_NAME" >/dev/null 2>&1 || true
claude_run mcp add "$MCP_NAME" -- "$CHIBI_CMD"

sync_claude_plugin

echo "Claude install complete. Restart Claude Code, then try: /chibi-mcp:chibi"
