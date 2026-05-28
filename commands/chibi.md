---
description: Show your active 치비, run a gacha, or open the collection.
---

Invoke the `chibi` skill to handle the user's request about their 치비 (chibi) desktop pet.

If the user typed `/chibi` with no arguments, default to showing the active character:
1. Call the `chibi` MCP server's `get_pet_state` tool.
2. Call `get_catalog` to look up the active character's `name_ko` and image.
3. Display the image (`![nickname](${CLAUDE_PLUGIN_ROOT}/assets/<id>.png)`) and a one-line mood label.

If the user passed arguments — e.g. `/chibi 뽑기`, `/chibi 보관함`, `/chibi 슬라이스` — route to the matching section of the `chibi` skill (gacha / collection / slice).

If there's no active character yet, run a free welcome gacha pull instead of erroring.
