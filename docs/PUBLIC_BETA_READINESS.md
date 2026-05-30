# Public Beta Readiness

This document is the pre-use gate for `chibi-mcp`. It is for free public beta
and pilot use only. It does not enable paid packs, checkout, license keys,
Sponsors tiers, team pricing, or paid random pulls.

## Current Readiness

Ready for:

- GitHub-based free installs for Claude Code, Codex, and VS Code.
- Local MCP use with no telemetry and localhost WebSocket defaults.
- Floating pet use on Linux, macOS, and Windows desktop sessions.
- VS Code `.vsix` packaging from GitHub Releases.
- Free creator/team pack validation and preview.
- Permissioned free pilots and showcase feedback.

Not ready for:

- A paid character store.
- Marketplace/Open VSX dependency as the only install path.
- macOS notarized public app distribution.
- Windows signed installer distribution.
- Paid support, license enforcement, or revenue share.

## Go/No-Go Command

Before a public release tag, run:

```bash
xvfb-run -a make public-beta-check
```

On a real desktop session, `xvfb-run` is optional:

```bash
make public-beta-check
```

This checks:

- shell and PowerShell installer syntax;
- Python lint, tests, wheel build, and `chibi-mcp --check`;
- creator/team pack validation and preview generation;
- share-card/social/lineup/options image generation;
- Claude and Codex plugin metadata smoke checks when the CLIs exist;
- desktop frontend lint;
- Rust/Tauri format and build checks;
- VS Code `.vsix` packaging;
- workflow, rights, and issue-form sanity;
- hidden-file brand identity scan so old names do not leak into `.github`,
  plugin metadata, or templates.

## Demo Assets

The public beta surface includes generated preview assets:

- `docs/demo.gif` — install/open/reaction loop preview.
- `docs/screenshots/vscode-sidebar.png`
- `docs/screenshots/claude-code.png`
- `docs/screenshots/codex-terminal.png`

These are generated from local project assets and verified by preflight. Before
a larger external launch, replace at least one generated preview with a real
user-captured desktop screenshot.

## Public Beta Acceptance Criteria

Ship a free public beta when all are true:

- `make public-beta-check` passes locally.
- GitHub Actions is green on the pushed commit.
- README shows install commands, screenshots, no-telemetry positioning, and
  no-monetization status.
- `chibi-audit` reports no paid core gate and no missing commercial-readiness
  files.
- Sample creator/team packs pass `chibi-pack validate --submission`.
- Issue templates exist for install problems, pack proposals, IP reports,
  team pilots, collaborations, and showcases.

## Release Tag Gate

After `main` is pushed and before creating a GitHub Release tag, run:

```bash
make release-check TAG=v1.4.19
```

This verifies version alignment, upstream state, tag availability, and the full
public beta preflight. See [RELEASE_PROCESS.md](RELEASE_PROCESS.md).

## Evidence To Collect After Launch

Use only public or user-submitted signals:

- GitHub stars, issues, traffic, and release downloads.
- VSIX download counts if Marketplace/Open VSX is added later.
- Showcase screenshots and user reports.
- Install success/failure reports by client and platform.
- Creator/team pack proposals that pass rights review.

Do not add hidden telemetry for beta measurement.
