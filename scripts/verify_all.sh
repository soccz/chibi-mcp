#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Shell scripts =="
bash -n "$ROOT"/scripts/*.sh

echo "== Python server =="
(
  cd "$ROOT/server"
  python -m ruff check .
  python -m pytest -q
  python -m py_compile chibi_mcp/__main__.py chibi_mcp/server.py chibi_mcp/window.py
  if [ -x venv/bin/python ]; then
    venv/bin/python -m build --wheel
  else
    python -m build --wheel
  fi
  python -m chibi_mcp --check
)

echo "== Claude plugin =="
if command -v claude >/dev/null 2>&1; then
  if command -v timeout >/dev/null 2>&1; then
    timeout 20s claude plugin validate "$ROOT"
  else
    claude plugin validate "$ROOT"
  fi
else
  echo "skip: claude CLI not found"
fi

echo "== Codex plugin =="
if command -v codex >/dev/null 2>&1; then
  tmp_home="$(mktemp -d)"
  HOME="$tmp_home" codex plugin marketplace add "$ROOT"
else
  echo "skip: codex CLI not found"
fi

echo "== Desktop frontend =="
(
  cd "$ROOT/desktop"
  npm run lint
)

echo "== Rust MCP prototype =="
if command -v cargo >/dev/null 2>&1; then
  (
    cd "$ROOT/server-rs"
    cargo fmt -- --check
    cargo clippy --all-targets -- -D warnings
  )
else
  echo "fail: cargo not found; install Rust to verify server-rs" >&2
  exit 1
fi

echo "== Tauri desktop Rust =="
if "$ROOT/scripts/check-linux-tauri-deps.sh" --soft; then
  if command -v cargo >/dev/null 2>&1; then
    (
      cd "$ROOT/desktop/src-tauri"
      cargo fmt -- --check
      cargo check --all-targets
    )
  else
    echo "fail: cargo not found; install Rust to verify Tauri desktop backend" >&2
    exit 1
  fi
elif [[ "${CHIBI_STRICT_RUNTIME:-0}" == "1" ]]; then
  "$ROOT/scripts/check-linux-tauri-deps.sh"
  exit 1
else
  echo "      run ./scripts/verify_runtime.sh to enforce local GUI/runtime readiness."
fi

echo "== Python floating window runtime =="
if python - <<'PY'
try:
    import tkinter  # noqa: F401
except Exception:
    raise SystemExit(2)
PY
then
  echo "tkinter ok"
elif [[ "${CHIBI_STRICT_RUNTIME:-0}" == "1" ]]; then
  python - <<'PY'
try:
    import tkinter  # noqa: F401
except Exception as exc:
    raise SystemExit(
        "fail: Python tkinter unavailable; open_pet_window will return a diagnostic instead of opening a Tk window. "
        "Ubuntu/Debian system Python: sudo apt-get install -y python3-tk. "
        "pyenv Python: install tk-dev, then rebuild Python. "
        f"({exc})"
    )
PY
  exit 1
else
  echo "skip: Python tkinter unavailable; open_pet_window returns a diagnostic instead of crashing."
  echo "      run ./scripts/verify_runtime.sh to enforce local GUI/runtime readiness."
fi

if command -v cargo >/dev/null 2>&1; then
  (
    cd "$ROOT/desktop/src-tauri"
    cargo fmt -- --check
  )
else
  echo "fail: cargo not found; install Rust to verify Tauri desktop formatting" >&2
  exit 1
fi

echo "== VS Code extension =="
(
  cd "$ROOT/vscode-ext"
  npm run lint
  npm run package
)

echo "== Workflow sanity =="
python - <<'PY'
from pathlib import Path

workflow = Path(".github/workflows/build.yml").read_text(encoding="utf-8")
required = [
    "vscode-package:",
    "needs: [desktop-build, vscode-package]",
    "vars.PUBLISH_PYPI == 'true'",
    "artifacts/**/*.vsix",
]
for item in required:
    assert item in workflow, item
print("workflow ok")
PY

echo "== GitHub issue forms =="
(
  cd "$ROOT/vscode-ext"
  node -e "const fs=require('fs'); const yaml=require('js-yaml'); for (const f of ['../.github/ISSUE_TEMPLATE/config.yml','../.github/ISSUE_TEMPLATE/bug_report.yml','../.github/ISSUE_TEMPLATE/install_problem.yml','../.github/ISSUE_TEMPLATE/character_pack.yml','../.github/ISSUE_TEMPLATE/showcase.yml']) { yaml.load(fs.readFileSync(f, 'utf8')); console.log('ok', f); }"
)

echo "all checks passed"
