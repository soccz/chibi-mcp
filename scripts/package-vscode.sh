#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/vscode-ext"

if [ ! -d node_modules ]; then
  npm ci
fi

npm run lint
npm run package

echo "VS Code package ready: $ROOT/vscode-ext/chibi-mcp-*.vsix"
