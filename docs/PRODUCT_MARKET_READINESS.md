# Product-Market Readiness

This document is a commercial-readiness scorecard for chibi-mcp. It does not enable monetization, paid packs, paid random pulls, Sponsors tiers, license keys, checkout, or team pricing.

## Current Position

chibi-mcp is commercially interesting because it sits between three behaviors:

- AI coding sessions are getting longer and more tool-driven.
- MCP/plugin ecosystems need trust signals because they can execute local code.
- Developers share cute, useful, and inspectable tools faster than generic productivity utilities.

The current product is strongest as:

> A local-first AI coding companion identity layer for Claude Code, Codex, and VS Code.

It is not ready to be marketed as a paid character store. It is ready for free public use, creator/team pack experiments, and permissioned pilot feedback.

Before broad sharing or a release tag, use [PUBLIC_BETA_READINESS.md](PUBLIC_BETA_READINESS.md) and run:

```bash
xvfb-run -a make public-beta-check
```

## Priority Customer Profiles

| Profile | Why they care | Current proof | Missing proof |
|---|---|---|---|
| Individual AI coding users | fun, status, session rhythm, local privacy | one-command install, pet window, gacha, options | demo GIF, repeated daily use evidence |
| Small dev teams | shared rituals, release/CI reactions, team mascot | sample team pack, `chibi-audit`, checksums | team install guide adoption feedback |
| Creator/artist pack authors | easy character pack format | `chibi-pack validate/preview`, issue template | first external pack submission |
| Devtool/keyboard/hackathon partners | distribution and culture fit | launch kit, asset terms, rights flow | partner proposal examples |
| Coding streamers | visual identity and overlay potential | local pet, share cards | browser/stream overlay mode later |

## Commercial Gaps

These are the highest-leverage gaps before any paid launch:

1. Demo proof: short GIF/video showing open, react, slice, option toggle, share card.
2. Activation proof: new user installs and sees value in under 5 minutes.
3. Retention proof: users return for slices, options, drops, and session rituals.
4. Team proof: one team can evaluate install, audit, and pack setup without maintainer hand-holding.
5. Creator proof: one non-maintainer can submit a rights-clean pack that passes validation.
6. Distribution proof: GitHub Release, VSIX, Claude/Codex plugin paths, and later Marketplace/Open VSX are clear.
7. Trust proof: no telemetry, localhost default, asset rights, and copycat response stay visible.

## No-Monetization Readiness Gates

Before charging for anything, collect evidence for:

- at least a few successful installs across Linux, macOS, and Windows;
- one Claude Code user, one Codex user, and one VS Code user reporting a working path;
- one external character/option idea submitted through the template;
- one team/admin evaluation using [TEAM_ADOPTION.md](TEAM_ADOPTION.md);
- one pilot report using the team pilot issue template;
- no unresolved high-severity install/security/right issues;
- repeatable `make check` and GitHub Actions success.

## What To Improve Next

Do now, without monetization:

- Keep the public beta preflight green before release tags.
- Add the demo GIF and real client screenshots.
- Invite free pilot feedback through `.github/ISSUE_TEMPLATE/team_pilot.yml`.
- Ask for showcase screenshots through `.github/ISSUE_TEMPLATE/showcase.yml`.
- Keep monthly drops free until there is traffic data.
- Use GitHub Traffic, issues, stars, release downloads, and Marketplace download counts only as aggregate external signals.

Do not do yet:

- price pages;
- checkout;
- license keys;
- paid random pulls;
- gated modes;
- creator revenue share;
- Sponsors tiers;
- team edition pricing.

## Source Notes

- GitHub Traffic shows views, clones, referrers, and popular content for recent repository activity: https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository
- GitHub repository topics help users discover projects by subject: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics
- VS Code documents packaging and publishing extensions with `vsce`: https://code.visualstudio.com/api/working-with-extensions/publishing-extension
- Open VSX is an open-source registry for VS Code-compatible editors: https://open-vsx.org/about
- Claude Code plugin marketplaces provide centralized discovery/versioning for plugins: https://code.claude.com/docs/en/plugin-marketplaces
