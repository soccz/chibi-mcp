# Team Adoption Guide

This guide helps a team evaluate chibi-mcp without enabling paid team pricing or gated features.

## Team Value

Teams should evaluate chibi-mcp for:

- a shared local AI coding companion for Claude Code, Codex, and VS Code;
- release, CI, and sprint rituals through character reactions and share cards;
- private mascot or project-themed character packs;
- no-telemetry local-first behavior that can be inspected before rollout.

## Admin Evaluation Checklist

Run from a clean machine or test workspace:

```bash
chibi-mcp --check
chibi-audit --json
```

Confirm:

- `telemetry` is `none`;
- WebSocket defaults to localhost;
- state file lives under the user profile;
- packaged asset catalog loads;
- `tkinter` is available if the floating window is required;
- Claude Code, Codex, or VS Code install path is documented for the team's platform.

## Rollout Paths

| Surface | Current path | Team note |
|---|---|---|
| Claude Code | `claude mcp add chibi -- chibi-mcp` | install server with `pipx` first |
| Codex | `codex mcp add chibi -- chibi-mcp` | same MCP server command |
| VS Code | `.vsix` via GitHub Release or local package | Marketplace/Open VSX publish remains a later decision |
| Desktop pet | Python tk window | requires a desktop session, not headless SSH |

## Team Pack Evaluation

Use the sample pack:

```bash
chibi-pack validate --submission examples/packs/team-sprint
chibi-pack preview examples/packs/team-sprint --out /tmp/team-sprint.html
```

For a private team mascot pack, require:

- transparent PNGs;
- `license`;
- `source_rights`;
- `rights_owner`;
- `asset_origin`;
- `permission_scope`;
- `no_third_party_ip: true`;
- no third-party logo/mascot unless the team has permission.

## Support Questions To Answer Before Paid Plans

Do not create team pricing yet. First collect:

- Which client is primary: Claude Code, Codex, VS Code, or mixed?
- Which platforms matter: Linux, macOS, Windows, WSL, dev containers?
- Is the pet window allowed, or MCP-only mode?
- Are private team assets acceptable in a local pack folder?
- Are release checksums enough, or is code signing required?
- Which admin policy blocks install: `pipx`, PowerShell, `.vsix`, MCP registration, or desktop GUI?

## Pilot Output

A useful team pilot should produce:

- install result per OS/client;
- `chibi-audit --json` output with private paths removed;
- one screenshot or share card if allowed;
- one list of blockers;
- one decision: keep using, pause, or needs specific change.

Use `.github/ISSUE_TEMPLATE/team_pilot.yml` for structured feedback.

## Source Notes

- GitHub Releases can attach downloadable assets for release distribution: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- VS Code supports installing extensions from `.vsix` files and the command line: https://code.visualstudio.com/docs/configure/extensions/extension-marketplace
- Claude Code plugin marketplaces support discovery and versioned plugin distribution: https://code.claude.com/docs/en/plugin-marketplaces
