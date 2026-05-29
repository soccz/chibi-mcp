#!/usr/bin/env python3
"""Generate a future HMAC secret for chibi license signing.

No paid entitlement gate is active in the open-source core. This script only
creates a secure secret for a future, user-approved commercial track. It does
not patch source code.

Usage:
    python scripts/rotate-hmac.py
    python scripts/rotate-hmac.py --bytes 48

After rotation, all previously-signed licenses are voided.
"""

from __future__ import annotations

import argparse
import datetime
import secrets
import sys


def generate_secret(byte_length: int = 32) -> str:
    return secrets.token_urlsafe(byte_length)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rotate chibi-mcp HMAC license secret")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Unsupported until a paid entitlement gate is explicitly approved",
    )
    parser.add_argument("--bytes", type=int, default=32, help="Secret entropy (bytes)")
    args = parser.parse_args(argv)

    if args.apply:
        print(
            "ERROR: --apply is disabled. The current open-source core has no paid "
            "entitlement gate to patch.",
            file=sys.stderr,
        )
        return 2

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
    print("No code was patched. Add build-time signing only after the user")
    print("explicitly approves a commercial entitlement design.")
    print()
    print("After rotation, previously-issued Pro licenses are voided.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
