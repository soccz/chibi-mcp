"""Release access policy for the open-source chibi-mcp catalog.

The current product decision is intentionally simple: all released starter
characters are free, and unreleased catalog placeholders stay hidden. Future
commercial packs may add signed entitlement checks, but no paid gate is active
in the open-source core.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime


@dataclasses.dataclass
class LicenseStatus:
    tier: str = "free"
    email: str | None = None
    expires: datetime | None = None
    reason: str | None = "open-source core; no paid entitlement gate"

    @property
    def is_pro(self) -> bool:
        return False


def verify_license() -> LicenseStatus:
    return LicenseStatus()


def filter_catalog_by_tier(catalog: dict, status: LicenseStatus) -> dict:
    """Return released characters from the catalog.

    `catalog` is the raw meta.json structure: { "characters": [ ... ],
    "options": [ ... ] } with tier metadata.

    `status` is accepted for API compatibility. The current open-source build
    returns released free characters only; upcoming placeholders are never
    returned to clients.
    """
    return {
        **catalog,
        "characters": [c for c in catalog["characters"] if c.get("tier") == "free"],
        "options": [o for o in catalog.get("options", []) if o.get("tier") == "free"],
    }
