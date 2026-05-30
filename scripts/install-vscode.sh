#!/usr/bin/env bash
set -euo pipefail

REPO="${CHIBI_GITHUB_REPO:-soccz/chibi-mcp}"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

need code
need curl

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "missing required command: python3 or python" >&2
  exit 1
fi

asset_url="$(
  curl -fsSL "$API_URL" | "$PYTHON_BIN" -c '
import json
import sys

release = json.load(sys.stdin)
for asset in release.get("assets", []):
    name = str(asset.get("name", ""))
    if name.endswith(".vsix"):
        print(asset["browser_download_url"])
        raise SystemExit(0)
raise SystemExit("No .vsix asset found in the latest GitHub Release.")
'
)"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
vsix="$tmpdir/chibi-mcp.vsix"

curl -fL "$asset_url" -o "$vsix"
code --install-extension "$vsix" --force

echo "VS Code install complete. Open the chibi activity bar view."
extensions="$(code --list-extensions 2>/dev/null || true)"
if printf '%s\n' "$extensions" | grep -qi '^soccz\.chibi-mcp$'; then
  echo "VS Code extension check: soccz.chibi-mcp installed."
else
  echo "warning: Could not verify soccz.chibi-mcp with code --list-extensions. Open VS Code once, then rerun if the chibi activity bar view is missing." >&2
fi
if command -v chibi-mcp >/dev/null 2>&1; then
  echo "Full cross-client diagnostics: chibi-mcp --doctor"
else
  echo "For Claude/Codex MCP diagnostics, install the chibi-mcp server, then run: chibi-mcp --doctor"
fi
