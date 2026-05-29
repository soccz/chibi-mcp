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
  ROOT="$ROOT" python - <<'PY'
import json
import os
import tomllib
from pathlib import Path

import chibi_mcp

root = Path(os.environ["ROOT"])
pyproject = tomllib.loads((root / "server" / "pyproject.toml").read_text(encoding="utf-8"))
server_version = pyproject["project"]["version"]
versions = {
    "server/chibi_mcp/__init__.py": chibi_mcp.__version__,
    ".claude-plugin/plugin.json": json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"],
    ".codex-plugin/plugin.json": json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"],
}
for source, version in versions.items():
    assert version == server_version, f"{source} version {version} != server/pyproject.toml {server_version}"
print(f"version metadata ok: {server_version}")
PY
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
        assert pack_main(["validate", str(example), "--submission"]) == 0
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
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops

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

root = Path.cwd()
with TemporaryDirectory() as home, TemporaryDirectory() as generated:
    os.environ["HOME"] = home
    os.environ["CHIBI_ASSET_DIR"] = str(root / "server" / "chibi_mcp" / "assets")
    sys.path.insert(0, str(root / "server"))
    from chibi_mcp.commercial import share_main
    from chibi_mcp.state import reset_state_for_tests

    reset_state_for_tests()
    generated_root = Path(generated)
    outputs = {
        "assets/social-preview.png": ["--preset", "social-preview"],
        "docs/screenshots/share-card.png": [],
        "docs/screenshots/starter-lineup.png": ["--preset", "lineup"],
        "docs/screenshots/option-showcase.png": ["--preset", "options"],
    }
    for rel, args in outputs.items():
        expected = generated_root / Path(rel).name
        assert share_main([*args, "--out", str(expected)]) == 0
        with Image.open(root / rel).convert("RGB") as actual, Image.open(expected).convert("RGB") as fresh:
            diff = ImageChops.difference(actual, fresh)
            assert diff.getbbox() is None, f"{rel} is stale; regenerate with chibi-share"
print("launch image assets ok")
PY

echo "== Brand identity sanity =="
ROOT="$ROOT" python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
legacy_terms = [
    "tteo" + "ki",
    "Tteo" + "ki",
    "떡" + "이",
    "치" + "비",
    "my_" + "tteok",
    "My " + "Tteok",
    "new " + "tteok character",
]
skip_dirs = {
    ".git",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "target",
    ".pytest_cache",
    "build",
    "dist",
    "venv",
}
skip_suffixes = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".vsix",
    ".lock",
    ".pyc",
}
violations = []
for path in root.rglob("*"):
    rel = path.relative_to(root)
    if any(part in skip_dirs for part in rel.parts):
        continue
    if not path.is_file() or path.suffix.lower() in skip_suffixes:
        continue
    try:
        raw = path.read_bytes()
    except OSError:
        continue
    if b"\0" in raw:
        continue
    text = raw.decode("utf-8", errors="ignore")
    for term in legacy_terms:
        if term in text:
            violations.append(f"{rel}: contains {term!r}")
            break

if violations:
    raise SystemExit("legacy brand identity found:\n" + "\n".join(violations))

public_surfaces = [
    "README.md",
    "INSTALL.md",
    "SPEC.md",
    "SPEC_V0.2.md",
    "CLAUDE.md",
    "CHARACTER_DESIGN.md",
    "STYLE_GUIDE.md",
    "PROCESS.md",
    "COMMERCIAL_STRATEGY.md",
    "GITHUB_STAR_STRATEGY.md",
    "server/README.md",
    "server/pyproject.toml",
    "server/chibi_mcp/__main__.py",
    "server/chibi_mcp/server.py",
    "server/chibi_mcp/window.py",
    "server/chibi_mcp/ws_server.py",
    "server-rs/src/main.rs",
    "desktop/README.md",
    "desktop/src-tauri/Cargo.toml",
    "desktop/src/index.html",
    "desktop/src/main.js",
    "desktop/src/preview.html",
    "vscode-ext/package.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    "commands/chibi.md",
    "skills/chibi/SKILL.md",
    "docs/CREATOR_PACKS.md",
    "docs/LAUNCH_KIT.md",
    "docs/PUBLIC_BETA_READINESS.md",
]
public_terms = [
    "Tteo" + "ki",
    "tteo" + "ki",
    "Korean rice cake",
    "rice cake",
    "rice-cake",
    "garaetteok",
    "tteok",
    "조청",
    "가래떡",
    "도막",
]
public_violations = []
for rel in public_surfaces:
    path = root / rel
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for term in public_terms:
        if term in text:
            public_violations.append(f"{rel}: contains public legacy concept {term!r}")
            break

if public_violations:
    raise SystemExit("public chibi branding drift found:\n" + "\n".join(public_violations))

catalog_display_surfaces = [
    "assets/meta.json",
    "server/chibi_mcp/assets/meta.json",
    "vscode-ext/resources/meta.json",
    "examples/packs/spring-hwajeon/meta.json",
    "examples/packs/team-sprint/meta.json",
]
catalog_display_terms = [
    *public_terms,
    "흰떡",
    "백설기",
    "무지개떡",
    "송편",
    "모찌",
    "rice syrup",
    "jocheong",
    "jocheong drip",
    "chapssaltteok",
    "tteokbokki",
    "injeolmi-style",
]
catalog_fields = {"name", "name_ko", "category", "description"}
catalog_violations = []
for rel in catalog_display_surfaces:
    path = root / rel
    catalog = json.loads(path.read_text(encoding="utf-8"))
    for section in ("characters", "options"):
        for index, item in enumerate(catalog.get(section, [])):
            if not isinstance(item, dict):
                continue
            for field in catalog_fields:
                value = str(item.get(field, ""))
                for term in catalog_display_terms:
                    if term.lower() in value.lower():
                        catalog_violations.append(
                            f"{rel}:{section}[{index}].{field} contains legacy display term {term!r}"
                        )
                        break

if catalog_violations:
    raise SystemExit("catalog display branding drift found:\n" + "\n".join(catalog_violations))
print("brand identity ok")
PY

echo "== Installer self-healing sanity =="
ROOT="$ROOT" python - <<'PY'
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
shared_required = [
    "setup_pipx",
    "repair_linux_tkinter",
    "python3-tkinter",
    "pacman -Sy --noconfirm tk",
    "zypper --non-interactive install python3-tk",
    "apk add py3-tkinter",
    "brew install",
]
for rel in ["scripts/install-claude.sh", "scripts/install-codex.sh"]:
    text = (root / rel).read_text(encoding="utf-8")
    missing = [item for item in shared_required if item not in text]
    assert not missing, f"{rel} missing {missing}"

windows_required = [
    "Install-PythonWithWinget",
    "winget install --exact --id Python.Python.3.13",
    "Ensure-Pipx",
    "ConvertFrom-Json",
]
for rel in ["scripts/install-claude.ps1", "scripts/install-codex.ps1"]:
    text = (root / rel).read_text(encoding="utf-8")
    missing = [item for item in windows_required if item not in text]
    assert not missing, f"{rel} missing {missing}"

print("installer self-healing ok")
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
        "macOS Homebrew Python: install the matching python-tk@X.Y package, such as python-tk@3.14. "
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
    "installer-syntax:",
    "Parse PowerShell installers",
    "needs: [desktop-build, vscode-package]",
    "vars.PUBLISH_PYPI == 'true'",
    "artifacts/**/*.vsix",
    "release-checksums/SHA256SUMS.txt",
    "sha256sum",
]
for item in required:
    assert item in workflow, item
print("workflow ok")
PY

echo "== Rights policy sanity =="
python - <<'PY'
import json
from pathlib import Path

required_docs = [
    "ASSET_RIGHTS.md",
    "OFFICIAL_ASSET_TERMS.md",
    "TRADEMARK.md",
    "COMMERCIAL_STRATEGY.md",
    "docs/PRODUCT_MARKET_READINESS.md",
    "docs/PUBLIC_BETA_READINESS.md",
    "docs/RELEASE_PROCESS.md",
    "docs/TEAM_ADOPTION.md",
    "docs/PILOT_PLAYBOOK.md",
    "docs/LAUNCH_KIT.md",
    "docs/CREATOR_PACKS.md",
    "docs/IP_AND_RIGHTS.md",
    "docs/COPYCAT_RESPONSE.md",
]
for rel in required_docs:
    assert Path(rel).exists(), rel

required_meta = {
    "license",
    "source_rights",
    "rights_owner",
    "asset_origin",
    "permission_scope",
    "no_third_party_ip",
}
for rel in [
    "assets/meta.json",
    "server/chibi_mcp/assets/meta.json",
    "vscode-ext/resources/meta.json",
    "examples/packs/spring-hwajeon/meta.json",
    "examples/packs/team-sprint/meta.json",
]:
    meta = json.loads(Path(rel).read_text(encoding="utf-8"))
    missing = required_meta - set(meta)
    assert not missing, f"{rel} missing {sorted(missing)}"
    assert meta["no_third_party_ip"] is True, rel
print("rights policy ok")
PY

echo "== GitHub YAML =="
(
  cd "$ROOT/vscode-ext"
  node -e "const fs=require('fs'); const yaml=require('js-yaml'); for (const f of ['../.github/release.yml','../.github/ISSUE_TEMPLATE/config.yml','../.github/ISSUE_TEMPLATE/bug_report.yml','../.github/ISSUE_TEMPLATE/install_problem.yml','../.github/ISSUE_TEMPLATE/feature_request.yml','../.github/ISSUE_TEMPLATE/character_pack.yml','../.github/ISSUE_TEMPLATE/ip_report.yml','../.github/ISSUE_TEMPLATE/team_pilot.yml','../.github/ISSUE_TEMPLATE/collaboration_idea.yml','../.github/ISSUE_TEMPLATE/showcase.yml']) { yaml.load(fs.readFileSync(f, 'utf8')); console.log('ok', f); }"
)

echo "all checks passed"
