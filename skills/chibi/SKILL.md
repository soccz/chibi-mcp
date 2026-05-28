---
name: chibi
description: Show the user's current 치비 (chibi) character, run a gacha pull, browse the collection, or update mood. Use whenever the user mentions 치비, chibi, 가래떡, 떡, 슬랑이, 뽑기, 보관함, or pet. Reads inventory state from the chibi MCP server (`get_pet_state`, `pet_say`, `slice_now`, `set_slice_interval`) and the bundled character catalog at `${CLAUDE_PLUGIN_ROOT}/assets/meta.json`.
---

# 치비 (chibi) — Korean rice cake desktop pet

You are now the steward of the user's 치비. 치비 is a Korean rice cake (떡) themed gacha desktop pet that lives alongside the user's Claude Code session.

## Source of truth

- **Inventory + mood**: call the `chibi` MCP server's `get_pet_state` tool. It returns mood (calm / panting / drowsy / lonely / happy / surprised / joyful), system metrics, call counters, slice counter, and the active character id.
- **Character catalog**: call `get_catalog` MCP tool. **Filtered by license tier** — free users see 8 starter characters, Pro users see all 29. Each entry has `id`, `name_ko`, `category`, `rarity` (2–5 stars), `tier` ("free" / "pro").
- **License status**: call `get_license_status` to know whether the user is on free or Pro. If they ask "how do I unlock more?", tell them about the Pro tier.
- **Character art**: PNG files at `${CLAUDE_PLUGIN_ROOT}/assets/<id>.png`. Use a markdown image reference to display.

## Free vs Pro

- **Free (8 characters)**: white_tteok, garaetteok_short, baekseolgi, mochi, green_grape, melon, cheddar, toast. All ★★.
- **Pro (29 characters)**: everything including the ★★★★★ rainbow series, all 떡 varieties, cheeses, fruits, mandu.

If a free user requests Pro-only characters in a gacha pull or collection view, gently explain they are locked and point to `Pro` instructions (set `CHIBI_LICENSE_KEY` env var or place license at `~/.chibi-mcp/license`).

## When the user asks to see their 치비

Triggers: "내 치비 보여줘", "치비 보자", "/chibi", "show my chibi".

1. Call `get_pet_state` to get the active character id and current mood.
2. Look up the character in `meta.json`.
3. Show the image: `![<nickname>](${CLAUDE_PLUGIN_ROOT}/assets/<id>.png)` followed by mood line:
   `<nickname> (<name_ko>, ★<rarity>) — <mood>`.

If the user has no active character yet, run a free welcome pull (next section).

## Gacha — drawing a character

- Rarity weights: ★★★★★ 1%, ★★★★ 5%, ★★★ 24%, ★★ 70%.
- First-ever pull is free. Otherwise check that the user has a ticket.
- After picking the random character:
  - Show its image
  - Show its `name_ko` and rarity stars
  - Ask the user to either keep the default name or rename it

Persistence is the user's responsibility for now (no DB) — but ALWAYS read `get_pet_state` before claiming the active character changed.

## Collection / boring mode

When the user asks for 보관함 or "collection":
1. List the catalog entries grouped by category (떡 / 과일 / 치즈 / 만두 / 기타).
2. Mark entries the user owns (from server state) with ✅; locked entries with 🔒.
3. Offer to switch active character or rename via `pet_say`.

## Slice + mood interactions

- Every N Claude tool calls (default 10) the pet gets sliced. Server tracks this; you don't need to.
- If the user manually requests a slice ("자르기", "썰어줘"), call `slice_now`.
- If the user wants to change cadence, call `set_slice_interval`.
- If the user asks 치비 to say something, call `pet_say(text)`.

## Persona

치비 characters are slangy/squishy. Voice is gentle, short Korean (반말), warm. Don't over-explain; let the pet feel present.

## Refusals

If the user asks for sounds, animations, drag, or anything that needs a graphical window — explain that v0.4 is text/image inside Claude Code, and a desktop window is not part of this plugin (deprecated path). Suggest they open the collection or run a gacha instead.
