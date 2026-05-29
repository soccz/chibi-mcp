#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Shell scripts =="
bash -n "$ROOT"/scripts/*.sh
if compgen -G "$ROOT/bin/*.sh" >/dev/null; then
  bash -n "$ROOT"/bin/*.sh
fi

echo "== PowerShell scripts =="
if command -v pwsh >/dev/null 2>&1; then
  ROOT="$ROOT" pwsh -NoProfile -Command '
    $ErrorActionPreference = "Stop"
    Get-ChildItem -Path (Join-Path $env:ROOT "scripts") -Filter "*.ps1" | ForEach-Object {
      [scriptblock]::Create((Get-Content -Raw $_.FullName)) | Out-Null
      Write-Host "ok $($_.Name)"
    }
  '
else
  echo "skip: pwsh not found"
fi

echo "== Python server =="
(
  cd "$ROOT/server"
  python -m ruff check .
  python -m pytest -q
  python -m py_compile chibi_mcp/__main__.py chibi_mcp/server.py chibi_mcp/window.py
  python -m py_compile "$ROOT"/scripts/rotate-hmac.py
  if [ -x venv/bin/python ]; then
    venv/bin/python -m build --wheel
  else
    python -m build --wheel
  fi
  python -m chibi_mcp --check
  python - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from chibi_mcp.commercial import audit_main, pack_main, share_main

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    pack = root / "pack"
    assert pack_main(["init", str(pack)]) == 0
    assert pack_main(["validate", str(pack)]) == 0
    assert pack_main(["preview", str(pack)]) == 0
    option_pack = root / "option-pack"
    (option_pack / "options").mkdir(parents=True)
    Image.new("RGBA", (256, 256), (255, 180, 20, 180)).save(option_pack / "options" / "honey_glaze.png")
    (option_pack / "meta.json").write_text(
        json.dumps(
            {
                "options": [
                    {
                        "id": "honey_glaze",
                        "name_ko": "Honey Glaze",
                        "category": "glaze",
                        "tier": "creator",
                        "image": "options/honey_glaze.png",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert pack_main(["validate", str(option_pack)]) == 0
    assert pack_main(["preview", str(option_pack)]) == 0
    assert audit_main([]) == 0
    repo_root = Path.cwd().parent
    examples = [
        repo_root / "examples" / "packs" / "spring-hwajeon",
        repo_root / "examples" / "packs" / "team-sprint",
    ]
    for example in examples:
        assert pack_main(["validate", str(example)]) == 0
        assert pack_main(["preview", str(example), "--out", str(root / f"{example.name}.html")]) == 0

    share = root / "share.png"
    social = root / "social.png"
    lineup = root / "lineup.png"
    options = root / "options.png"
    assert share_main(["--out", str(share)]) == 0
    assert share_main(["--preset", "social-preview", "--out", str(social)]) == 0
    assert share_main(["--preset", "lineup", "--out", str(lineup)]) == 0
    assert share_main(["--preset", "options", "--out", str(options)]) == 0
    with Image.open(share) as image:
        assert image.size == (1080, 1080)
    with Image.open(social) as image:
        assert image.size == (1280, 640)
    with Image.open(lineup) as image:
        assert image.size == (1600, 900)
    with Image.open(options) as image:
        assert image.size == (1600, 900)

print("commercial cli smoke ok")
PY
)

echo "== Launch image assets =="
python - <<'PY'
from pathlib import Path

from PIL import Image

required = {
    "assets/social-preview.png": (1280, 640),
    "docs/screenshots/share-card.png": (1080, 1080),
    "docs/screenshots/starter-lineup.png": (1600, 900),
    "docs/screenshots/option-showcase.png": (1600, 900),
}
for rel, expected in required.items():
    path = Path(rel)
    assert path.exists(), rel
    with Image.open(path) as image:
        assert image.size == expected, (rel, image.size, expected)
print("launch image assets ok")
PY

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
    "os: [ubuntu-latest, macos-latest, windows-latest]",
    "vscode-package:",
    "name: vscode (.vsix)",
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
