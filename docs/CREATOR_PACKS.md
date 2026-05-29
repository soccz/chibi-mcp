# Creator and Team Pack Guide

`chibi-mcp` should feel like a character platform before it becomes a store. The pack format is intentionally simple: a folder with `meta.json`, transparent PNGs, and a generated preview.

This is a commercial-readiness surface, not a paid gate. The base app, MCP tools, modes, starter characters, and free options stay free. Do not add paid packs, paid pulls, Sponsors tiers, license keys, or creator revenue share unless the user explicitly approves monetization later.

## Pack Types

| Pack type | Example | Business value | Status |
|---|---|---|---|
| Free monthly drop | new tteok character or option | repeat visits, GitHub shares | ready via `meta.json` |
| Creator pack | artist-made character/option set | external content supply | ready via validator |
| Team pack | private mascot, release badge | B2B admin value | ready via validator |
| Brand collab | keycap/cafe/devtool skin | distribution partner | strategy only |
| Direct purchase pack | fixed-price cosmetics | out of scope for now | do not implement |

## Runnable Examples

```bash
chibi-pack validate examples/packs/spring-hwajeon
chibi-pack preview examples/packs/spring-hwajeon --out /tmp/spring-preview.html

chibi-pack validate examples/packs/team-sprint
chibi-pack preview examples/packs/team-sprint --out /tmp/team-preview.html
```

Included examples:

- `examples/packs/spring-hwajeon` — seasonal creator pack with one character and one flower option.
- `examples/packs/team-sprint` — team pack with one sprint mascot and one release badge option.

## Required Structure

```text
my-pack/
├── meta.json
├── my_character.png
└── options/
    └── my_option.png
```

`meta.json` supports two top-level arrays:

- `characters[]`: `id`, `name_ko`, `category`, `rarity`, `tier`, `image`
- `options[]`: `id`, `name_ko`, `category`, `tier`, `image`

IDs must be lowercase slugs. PNGs should be transparent, square, and at least 128×128. The official starter assets use 512×512.

## Submission Checklist

- Artwork is original, commissioned, or permissioned.
- No copyrighted third-party characters, logos, or mascots without rights.
- PNG background is transparent.
- Character is readable at 80px, because the VS Code sidebar and share cards use small previews.
- Option layer works over the default `garaetteok_short` body.
- Pack passes `chibi-pack validate <dir>`.
- Preview HTML is attached to the issue or PR.

## Review Labels

Use these labels when triaging a pack proposal:

- `character-pack`
- `option-layer`
- `creator-pack`
- `team-pack`
- `collaboration`
- `rights-needed`
- `ready-for-preview`

## Commercial Guardrails

- Do not introduce paid random pulls.
- Do not lock Pet / Notification / Widget / VTuber modes.
- Do not add paid packs, checkout, Sponsors tiers, license keys, or creator revenue share yet.
- Do not add telemetry to measure pack usage.
- Keep any future sponsor credit inside catalog/README/release notes, not as workflow interruption, and only after approval.

## Source Notes

- Claude Code plugin marketplaces support distributing plugins to teams and communities: https://code.claude.com/docs/en/plugin-marketplaces
- Claude plugin submission is surfaced through the community plugin directory and Claude Code marketplace: https://claude.com/docs/plugins/submit
- GitHub issue forms standardize creator submissions: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository
