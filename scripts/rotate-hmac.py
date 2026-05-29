#!/usr/bin/env python3
"""Generate a fresh HMAC secret for chibi Pro license signing.

The current placeholder in `server/chibi_mcp/license.py` is intentionally
not a real secret. This script produces a secure replacement and prints
the exact next steps. Run before any production Pro launch.

Usage:
    python scripts/rotate-hmac.py
    python scripts/rotate-hmac.py --apply   # also patches license.py

After rotation, all previously-signed licenses are voided.
"""

from __future__ import annotations

import argparse
import datetime
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LICENSE_FILE = REPO_ROOT / "server" / "chibi_mcp" / "license.py"
SECRET_MARKER = b'_HMAC_SECRET = b"'


def generate_secret(byte_length: int = 32) -> str:
    return secrets.token_urlsafe(byte_length)


def patch_license(new_secret: str) -> bool:
    src = LICENSE_FILE.read_bytes()
    if SECRET_MARKER not in src:
        print(f"ERROR: {LICENSE_FILE} does not contain the secret marker", file=sys.stderr)
        return False
    head, _, rest = src.partition(SECRET_MARKER)
    _, _, tail = rest.partition(b'"')
    new_line = SECRET_MARKER + new_secret.encode() + b'"'
    LICENSE_FILE.write_bytes(head + new_line + tail)
    print(f"patched {LICENSE_FILE}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rotate chibi-mcp HMAC license secret")
    parser.add_argument("--apply", action="store_true", help="Patch license.py in place")
    parser.add_argument("--bytes", type=int, default=32, help="Secret entropy (bytes)")
    args = parser.parse_args(argv)

    secret = generate_secret(args.bytes)
    today = datetime.date.today().isoformat()

    print("=" * 64)
    print(f"New HMAC secret (generated {today})")
    print("=" * 64)
    print(secret)
    print()
    print("Add this to GitHub Actions Secrets (do NOT commit):")
    print("  Repository Settings > Secrets > Actions > New secret")
    print("  Name:  CHIBI_HMAC_SECRET")
    print(f"  Value: {secret}")
    print()
    print("Then either:")
    print("  (a) Build-time substitution: have CI sed-replace the placeholder")
    print("      before `python -m build`.")
    print("  (b) For local testing only: rerun this script with --apply.")
    print()
    print("After rotation, previously-issued Pro licenses are voided.")

    if args.apply:
        print()
        print("Patching license.py in place — DO NOT commit this change.")
        return 0 if patch_license(secret) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
