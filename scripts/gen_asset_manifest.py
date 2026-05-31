#!/usr/bin/env python3
"""Generate ASSET_MANIFEST.sha256 for the official asset directories.

The manifest pins the sha256 of every catalog-referenced official image
(characters + option layers) so tampering or drift is detectable offline by
`chibi-check`, `verify_all.sh`, and disputes over provenance. The format is
`sha256sum -c` compatible.

Re-run after an *intentional* official-art change and commit the updated
manifests. Launch/social/demo images are intentionally excluded (they are
regenerated and pixel-diffed elsewhere), so this baseline stays stable.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ASSET_DIRS = [
    "assets",
    "server/chibi_mcp/assets",
    "vscode-ext/resources",
]


def manifest_lines(asset_dir: Path) -> list[str]:
    meta = json.loads((asset_dir / "meta.json").read_text(encoding="utf-8"))
    seen: set[str] = set()
    lines: list[str] = []
    for item in meta.get("characters", []) + meta.get("options", []):
        image = item.get("image")
        if not image or image in seen:
            continue
        path = asset_dir / image
        if not path.exists():
            continue
        seen.add(image)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {image}")
    return sorted(lines)


def write_manifest(asset_dir: Path) -> int:
    lines = manifest_lines(asset_dir)
    (asset_dir / "ASSET_MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    for rel in ASSET_DIRS:
        asset_dir = root / rel
        if not (asset_dir / "meta.json").exists():
            print(f"skip (no meta.json): {rel}", file=sys.stderr)
            continue
        count = write_manifest(asset_dir)
        print(f"wrote {rel}/ASSET_MANIFEST.sha256 ({count} assets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
