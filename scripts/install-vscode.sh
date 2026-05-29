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

echo "VS Code install complete. Open the tteoki activity bar view."
