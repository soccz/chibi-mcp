---
description: Open chibi, run a gacha pull, manage options, or show the collection.
---

Handle this command directly. You are already inside the Claude slash command, so **do not invoke another slash command** such as `/chibi`, and do not report `Unknown command: /chibi`.

First interpret the user's raw arguments after `/chibi-mcp:chibi`.

If there are no arguments, or the user typed `보여줘`, `open`, or `show`, default to **opening the floating window**:
1. Call the `chibi` MCP server's `open_pet_window` tool (no args).
2. Send a one-line confirmation: `<name_ko> ★<rarity> — <mood_ko>`.

If `open_pet_window` returns `opened: false`, do not pretend the pet opened.
Report the returned `reason` plus `next_step` or `log_path` when present, and
tell the user to run `chibi-mcp --open` in a terminal for a direct window test.
Only run a free welcome gacha pull if the reason says there are no released
characters or no character is available.

If the user passed arguments, route directly:

- `뽑기`, `pull`, `gacha` → `pull_gacha`; if `drawn` is not null, treat `active_character_id` as the newly selected visible chibi and mention that it was saved to the collection.
- `보관함`, `collection`, `inventory` → `get_inventory` + `get_catalog`
- `마일스톤`, `반응해`, `milestone` → `slice_now`
- `닫기`, `close` → `close_pet_window`
- `말해 <text>`, `say <text>` → `pet_say(text)`
- `옵션`, `토핑`, `꿀`, `비즈` → `get_options`, then use `set_active_options` if the user names options

Keep the response compact and pet-like. Do not explain MCP internals unless the command fails.
