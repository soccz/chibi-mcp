# Launch Kit

This is the practical launch kit for turning `chibi-mcp` from a cute MVP into an installable, shareable product. It prepares distribution and content surfaces without turning on paid gates.

Monetization is explicitly deferred. Do not add paid packs, paid random pulls, Sponsors tiers, license keys, checkout, team pricing, or creator revenue share unless the user approves that later.

## Positioning

One-line:

> The cutest local MCP companion for Claude Code, Codex, and VS Code.

Short copy:

> `chibi-mcp` adds a local rice-cake desktop pet to AI coding sessions. It reacts to CPU, battery, idle time, and tool calls; collects characters; applies free option layers; and stays no-telemetry by default.

Trust copy:

> Localhost-first. No telemetry. Open source. `chibi-audit` and `chibi-mcp --check` make install state visible before teams roll it out.

## Channel Matrix

| Channel | Why it matters | Current repo surface | Next action |
|---|---|---|---|
| GitHub Release | default open-source install path | wheel, `.vsix`, screenshots, docs | tag release with checksums |
| Claude Code marketplace | native Claude discovery | `.claude-plugin`, hooks, MCP | submit after demo GIF |
| Codex plugin marketplace | Codex-native install path | `.codex-plugin`, skill, MCP | keep metadata polished |
| VS Code Marketplace | search/install inside VS Code | `vscode-ext`, `vsce package` | publish after publisher token decision |
| Open VSX | VS Code-compatible OSS editors | same `.vsix` package | publish after namespace/token decision |
| GitHub Sponsors | possible future support path | documented only | do not enable yet |
| Creator packs | content supply | `chibi-pack validate/preview` | invite sample submissions |
| Team packs | B2B admin value | `chibi-audit`, sample team pack | write admin install note |

## Assets To Ship

Already generated:

- `assets/social-preview.png` — 1280×640 social preview
- `docs/screenshots/share-card.png` — 1080×1080 share card
- `docs/screenshots/starter-lineup.png` — 1600×900 starter lineup
- `docs/screenshots/option-showcase.png` — 1600×900 option showcase

Still needed before public push:

- `docs/demo.gif` — pet opens, option toggles, slice event, share card
- `docs/screenshots/vscode-sidebar.png`
- `docs/screenshots/claude-code.png`
- `docs/screenshots/codex-terminal.png`

## Launch Checklist

1. Run `xvfb-run -a make strict-check`.
2. Run `xvfb-run -a ./scripts/verify_runtime.sh`.
3. Generate release assets with `chibi-share`.
4. Package VS Code extension with `./scripts/package-vscode.sh`.
5. Validate sample packs:
   - `chibi-pack validate examples/packs/spring-hwajeon`
   - `chibi-pack validate examples/packs/team-sprint`
6. Tag a GitHub Release with wheel, `.vsix`, checksums, and screenshots.
7. Update GitHub social preview using `assets/social-preview.png`.
8. Set topics: `mcp`, `model-context-protocol`, `claude-code`, `codex`, `vscode-extension`, `local-first`, `no-telemetry`, `desktop-pet`, `ai-agent`.
9. Open a pinned "Show your tteoki" issue or Discussion.

## Post Copy

GitHub/X short:

```text
I made chibi-mcp: a no-telemetry local MCP pet for Claude Code, Codex, and VS Code.

It reacts to CPU/battery/tool calls, gets sliced every N calls, has gacha characters, and now ships with 12 free visual option layers.

GitHub: https://github.com/soccz/chibi-mcp
```

Korean short:

```text
Claude Code / Codex / VS Code에서 돌아가는 로컬 MCP 펫 만들었습니다.

떡이(tteoki)가 CPU·배터리·툴 호출에 반응하고, N번 호출마다 도막나고, 캐릭터/옵션팩까지 확장됩니다. telemetry 없음.

https://github.com/soccz/chibi-mcp
```

## Source Notes

- VS Code documents `vsce package` / `vsce publish` and Marketplace publishing requirements: https://code.visualstudio.com/api/working-with-extensions/publishing-extension
- Open VSX is an open-source registry for VS Code-compatible editors: https://open-vsx.org/about
- Open VSX publishing uses the `ovsx` CLI and can publish an existing `.vsix`: https://github.com/eclipse/openvsx/wiki/Publishing-Extensions
- Claude Code plugin marketplaces provide centralized discovery/versioning for teams and communities: https://code.claude.com/docs/en/plugin-marketplaces
- Claude plugin submission can target the community plugin directory surfaced in Claude Code: https://claude.com/docs/plugins/submit
- GitHub Sponsors supports one-time or monthly sponsorship tiers for open-source maintainers, but chibi-mcp should not enable it yet: https://docs.github.com/en/sponsors/getting-started-with-github-sponsors/about-github-sponsors
