#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Public beta preflight =="

if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT" diff --check
  if [ -n "$(git -C "$ROOT" status --short)" ]; then
    echo "note: working tree has uncommitted changes; continuing so this can run inside a PR."
  fi
fi

echo "== Strict source/runtime verification =="
CHIBI_STRICT_RUNTIME=1 "$ROOT/scripts/verify_all.sh"

echo "== Public surface checklist =="
ROOT="$ROOT" python - <<'PY'
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
required = [
    "README.md",
    "INSTALL.md",
    "SECURITY.md",
    "ASSET_RIGHTS.md",
    "OFFICIAL_ASSET_TERMS.md",
    "TRADEMARK.md",
    "docs/PRODUCT_MARKET_READINESS.md",
    "docs/PUBLIC_BETA_READINESS.md",
    "docs/PILOT_PLAYBOOK.md",
    "docs/TEAM_ADOPTION.md",
    "docs/CREATOR_PACKS.md",
    "docs/IP_AND_RIGHTS.md",
    "docs/COPYCAT_RESPONSE.md",
    "docs/LAUNCH_KIT.md",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/install_problem.yml",
    ".github/ISSUE_TEMPLATE/character_pack.yml",
    ".github/ISSUE_TEMPLATE/ip_report.yml",
    ".github/ISSUE_TEMPLATE/team_pilot.yml",
    ".github/ISSUE_TEMPLATE/collaboration_idea.yml",
    ".github/ISSUE_TEMPLATE/showcase.yml",
    "assets/social-preview.png",
    "docs/screenshots/share-card.png",
    "docs/screenshots/starter-lineup.png",
    "docs/screenshots/option-showcase.png",
]
missing = [rel for rel in required if not (root / rel).exists()]
if missing:
    raise SystemExit("missing required public beta surface:\n" + "\n".join(missing))

readme = (root / "README.md").read_text(encoding="utf-8")
for phrase in [
    "no telemetry",
    "Monetization is not enabled",
    "Claude Code",
    "Codex",
    "VS Code",
    "chibi-mcp --check",
]:
    if phrase not in readme:
        raise SystemExit(f"README.md is missing required public signal: {phrase!r}")

optional = [
    "docs/demo.gif",
    "docs/screenshots/vscode-sidebar.png",
    "docs/screenshots/claude-code.png",
    "docs/screenshots/codex-terminal.png",
]
optional_missing = [rel for rel in optional if not (root / rel).exists()]
if optional_missing:
    print("manual demo assets still recommended before broad launch:")
    for rel in optional_missing:
        print(f"- {rel}")

print("public beta surface ok")
PY

echo "public beta preflight passed"
