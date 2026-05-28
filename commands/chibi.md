---
description: Show your active 치비, run a gacha, or open the collection.
---

Invoke the `chibi` skill to handle the user's request about their 치비 (chibi) desktop pet.

If the user typed `/chibi` with no arguments, default to **opening the floating window**:
1. Call the `chibi` MCP server's `open_pet_window` tool (no args).
2. Send a one-line confirmation: `<name_ko> ★<rarity> — 기분: <mood>` from the tool's return value.

If `open_pet_window` returns `opened: false` (no character yet), run a free welcome gacha pull instead.

If the user passed arguments — e.g. `/chibi 뽑기`, `/chibi 보관함`, `/chibi 슬라이스`, `/chibi 닫기` — route to the matching section of the `chibi` skill (gacha / collection / slice / close_pet_window).
