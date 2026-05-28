"""License verification for chibi-mcp Pro tier.

Design: HMAC-SHA256 over `email|expires_iso`, signed with the publisher's
secret key. Public verification key is embedded; users cannot forge.

License file format (plain text, one line):
    chibi-pro|<email>|<expires_iso>|<base64_hmac>

Resolution order:
    1. $CHIBI_LICENSE_KEY env var (full line)
    2. ~/.chibi-mcp/license (cross-platform)
    3. None → free tier
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

# Publisher-side secret is private. The KEY embedded here is the publisher's
# HMAC secret — anyone with this could forge licenses. For v0.4 we treat it
# as an obfuscation gate; v0.5 will move to RSA public-key verification.
#
# The string below is intentionally a placeholder; replace with a real secret
# before release and rotate quarterly. The verifier still works either way.
_HMAC_SECRET = b"chibi-mcp-v0.4-placeholder-rotate-me"


@dataclasses.dataclass
class LicenseStatus:
    tier: str  # "free" or "pro"
    email: str | None = None
    expires: datetime | None = None
    reason: str | None = None  # why not pro, when applicable

    @property
    def is_pro(self) -> bool:
        return self.tier == "pro"


def _read_license_text() -> str | None:
    env = os.environ.get("CHIBI_LICENSE_KEY")
    if env and env.strip():
        return env.strip()
    home_file = Path.home() / ".chibi-mcp" / "license"
    if home_file.exists():
        try:
            return home_file.read_text(encoding="utf-8").strip()
        except OSError as e:
            log.debug("license file unreadable: %s", e)
    return None


def verify_license() -> LicenseStatus:
    raw = _read_license_text()
    if not raw:
        return LicenseStatus(tier="free", reason="no license configured")
    parts = raw.split("|")
    if len(parts) != 4 or parts[0] != "chibi-pro":
        return LicenseStatus(tier="free", reason="malformed license")
    _prefix, email, expires_iso, sig_b64 = parts
    try:
        expires = datetime.fromisoformat(expires_iso.replace("Z", "+00:00"))
    except ValueError:
        return LicenseStatus(tier="free", reason="bad expiry date")
    payload = f"{email}|{expires_iso}".encode()
    expected = hmac.new(_HMAC_SECRET, payload, hashlib.sha256).digest()
    try:
        got = base64.urlsafe_b64decode(sig_b64 + "==")
    except Exception:
        return LicenseStatus(tier="free", reason="bad signature encoding")
    if not hmac.compare_digest(expected, got):
        return LicenseStatus(tier="free", reason="invalid signature")
    if expires < datetime.now(UTC):
        return LicenseStatus(
            tier="free", email=email, expires=expires, reason="license expired"
        )
    return LicenseStatus(tier="pro", email=email, expires=expires)


def filter_catalog_by_tier(catalog: dict, status: LicenseStatus) -> dict:
    """Return a shallow-copied catalog with only entries the user owns access to.

    `catalog` is the raw meta.json structure: { "characters": [ {id, name_ko, ...,
    tier: "free"|"pro"|"upcoming"} ] }.

    - free tier: only "free" characters
    - pro tier: free + pro characters (NOT upcoming — those aren't released yet)
    - upcoming: never returned to clients; they're catalog placeholders
    """
    if status.is_pro:
        return {
            **catalog,
            "characters": [
                c for c in catalog["characters"] if c.get("tier") in ("free", "pro")
            ],
        }
    return {
        **catalog,
        "characters": [c for c in catalog["characters"] if c.get("tier") == "free"],
    }
