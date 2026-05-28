---
description: Show your active 치비, run a gacha, or open the collection.
---

Invoke the `chibi` skill to handle the user's request about their 치비 (chibi) desktop pet.

If the user typed `/chibi` with no arguments, default to **opening the floating window**:
1. Call the `chibi` MCP server's `open_pet_window` tool (no args).
2. Send a one-line confirmation: `<name_ko> ★<rarity> — <mood_ko>`.

If `open_pet_window` returns `opened: false` (no character yet), run a free welcome gacha pull instead.

If the user passed arguments, route directly:

- `/chibi 뽑기`, `/chibi pull` → `pull_gacha`
- `/chibi 보관함`, `/chibi collection` → `get_inventory` + `get_catalog`
- `/chibi 잘라줘`, `/chibi 슬라이스` → `slice_now`
- `/chibi 닫기`, `/chibi close` → `close_pet_window`
- `/chibi 말해 <text>` → `pet_say(text)`

Keep the response compact and pet-like. Do not explain MCP internals unless the command fails.
