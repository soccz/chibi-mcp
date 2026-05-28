#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${CHIBI_REPO_URL:-git+https://github.com/soccz/chibi-mcp.git#subdirectory=server}"
MARKETPLACE="${CHIBI_MARKETPLACE:-soccz/chibi-mcp}"
MCP_NAME="${CHIBI_MCP_NAME:-chibi}"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

need pipx
need codex

find_chibi_cmd() {
  if command -v chibi-mcp >/dev/null 2>&1; then
    command -v chibi-mcp
    return 0
  fi

  local pipx_bin
  pipx_bin="$(pipx environment --value PIPX_BIN_DIR 2>/dev/null || true)"

  local user_base
  user_base="$(python3 -m site --user-base 2>/dev/null || true)"

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

if pipx list --short 2>/dev/null | awk '{print $1}' | grep -qx "chibi-mcp"; then
  pipx upgrade chibi-mcp || pipx reinstall chibi-mcp
else
  pipx install "$REPO_URL"
fi

CHIBI_CMD="$(find_chibi_cmd)"
"$CHIBI_CMD" --check

if codex mcp get "$MCP_NAME" >/dev/null 2>&1; then
  echo "Codex MCP '$MCP_NAME' already exists."
else
  codex mcp add "$MCP_NAME" -- "$CHIBI_CMD"
fi

codex plugin marketplace add "$MARKETPLACE" || true

echo "Codex install complete. Try: 내 치비 보여줘"
