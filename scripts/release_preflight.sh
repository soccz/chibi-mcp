#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALLOW_DIRTY=0
RUN_PUBLIC_BETA=1
TAG=""

usage() {
  cat <<'EOF'
Usage: scripts/release_preflight.sh [vX.Y.Z] [--allow-dirty] [--skip-public-beta]

Checks release-tag readiness before pushing a GitHub Release tag.

Options:
  --allow-dirty        Do not fail on uncommitted changes. Useful while editing this script.
  --skip-public-beta   Skip the expensive public beta preflight. Useful for quick version checks.
  -h, --help           Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --allow-dirty)
      ALLOW_DIRTY=1
      ;;
    --skip-public-beta)
      RUN_PUBLIC_BETA=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    v*)
      if [ -n "$TAG" ]; then
        echo "fail: release tag specified more than once" >&2
        exit 1
      fi
      TAG="$1"
      ;;
    *)
      echo "fail: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

SERVER_VERSION="$(
  ROOT="$ROOT" python - <<'PY'
import os
import tomllib
from pathlib import Path

root = Path(os.environ["ROOT"])
data = tomllib.loads((root / "server" / "pyproject.toml").read_text(encoding="utf-8"))
print(data["project"]["version"])
PY
)"

if [ -z "$TAG" ]; then
  TAG="v$SERVER_VERSION"
fi

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "fail: tag must look like vX.Y.Z, got $TAG" >&2
  exit 1
fi

TAG_VERSION="${TAG#v}"
if [ "$TAG_VERSION" != "$SERVER_VERSION" ]; then
  echo "fail: tag $TAG does not match server version $SERVER_VERSION" >&2
  exit 1
fi

echo "== Release preflight: $TAG =="

echo "== Version sanity =="
ROOT="$ROOT" TAG="$TAG" python - <<'PY'
import json
import os
import tomllib
from pathlib import Path

root = Path(os.environ["ROOT"])
tag = os.environ["TAG"]
server = tomllib.loads((root / "server" / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
claude = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
codex = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
vscode = json.loads((root / "vscode-ext" / "package.json").read_text(encoding="utf-8"))["version"]
desktop = tomllib.loads((root / "desktop" / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8"))["package"]["version"]

if claude != server:
    raise SystemExit(f".claude-plugin/plugin.json version {claude} != server version {server}")
if codex != server:
    raise SystemExit(f".codex-plugin/plugin.json version {codex} != server version {server}")

print(f"tag: {tag}")
print(f"server/python: {server}")
print(f"claude plugin: {claude}")
print(f"codex plugin: {codex}")
print(f"vscode extension: {vscode}")
print(f"desktop app: {desktop}")
PY

echo "== Git sanity =="
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT" diff --check

  if [ "$ALLOW_DIRTY" -eq 0 ] && [ -n "$(git -C "$ROOT" status --short)" ]; then
    echo "fail: working tree is not clean" >&2
    git -C "$ROOT" status --short >&2
    exit 1
  fi

  if git -C "$ROOT" rev-parse --verify "$TAG" >/dev/null 2>&1; then
    echo "fail: local tag already exists: $TAG" >&2
    exit 1
  fi

  branch="$(git -C "$ROOT" branch --show-current || true)"
  if [ "$branch" != "main" ]; then
    echo "warning: current branch is '$branch', not 'main'"
  fi

  if git -C "$ROOT" rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    local_head="$(git -C "$ROOT" rev-parse HEAD)"
    upstream_head="$(git -C "$ROOT" rev-parse '@{u}')"
    if [ "$local_head" != "$upstream_head" ]; then
      echo "fail: local HEAD does not match upstream. Push main before tagging." >&2
      echo "local:    $local_head" >&2
      echo "upstream: $upstream_head" >&2
      exit 1
    fi
  else
    echo "warning: no upstream branch configured; cannot compare origin/main"
  fi
else
  echo "warning: not inside a git worktree; skipping git sanity"
fi

if [ "$RUN_PUBLIC_BETA" -eq 1 ]; then
  echo "== Public beta gate =="
  if command -v xvfb-run >/dev/null 2>&1; then
    xvfb-run -a make -C "$ROOT" public-beta-check
  else
    make -C "$ROOT" public-beta-check
  fi
else
  echo "skip: public beta gate"
fi

cat <<EOF
release preflight passed for $TAG

Next commands:
  git tag $TAG
  git push origin $TAG
EOF
