# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`chibi-mcp` is an MCP server + cross-platform desktop character ("chibi") that surfaces system state (CPU, battery, session) through a character with personality. It is installed from GitHub for Claude Code, Codex, and VS Code, and runs a local server/window that talks over localhost where a desktop session is available.

The project now has an executable Python MCP server, Claude/Codex plugin metadata, a VS Code `.vsix` packaging path, and a floating pet window implemented in pure Python (tk + Pillow + PyObjC for macOS transparency) spawned as a detached subprocess by the MCP server. A legacy Tauri attempt remains under `desktop/` for v0.1–v0.2 reference but is not part of the current install path. Some docs still describe future product phases; check the current files before assuming a phase boundary.

## Repository structure

- `SPEC.md` — the source of truth for **what the user has actually asked for** and **what was jointly decided** vs **what is still undecided**. Read this first.
- `CHARACTER_DESIGN.md` — character specifications (proportions, expressions, motions, sounds, palette). This is the **delegated design domain** (the user explicitly delegated design to Claude).
- `STYLE_GUIDE.md` — UI, typography, voice, share-card design. Also delegated design domain.
- `PROCESS.md` — Step A through Step G. Step F/G are commercial and GitHub growth strategy, not approved monetization implementation.
- `COMMERCIAL_STRATEGY.md` — commercial expansion candidates and guardrails.
- `GITHUB_STAR_STRATEGY.md` — source-backed GitHub growth plan, topics, community surface, launch loop.
- `INSTALL.md` — GitHub install matrix for Claude Code, Codex, and VS Code.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/` — public community and trust surface.
- `server/` — Python MCP server package. Also ships the floating pet window (`chibi_mcp/window.py`), the `chibi-say` CLI used by hooks, and the `chibi-check` self-diagnostic.
- `hooks/`, `bin/` — Claude Code plugin hooks bridge: `hooks/hooks.json` fires `bin/chibi-react.sh` on PreToolUse / PostToolUse, which forwards a contextual phrase via `chibi-say` to the floating window.
- `vscode-ext/` — VS Code extension packaging path. As of 0.5.0 also calls `chibi-say` on save / task / debug events.
- `desktop/` — legacy Tauri client; archival only.
- `assets/` and `server/chibi_mcp/assets/` — starter PNG characters and metadata.

Core commands:

- Full verification: `make check` or `./scripts/verify_all.sh`
- Python tests: `cd server && python -m pytest -q`
- Server health check: `cd server && python -m chibi_mcp --check`
- Commercial-readiness CLIs: `chibi-audit`, `chibi-pack init/validate/preview <dir>`, `chibi-share --out share-card.png`, `chibi-share --preset social-preview --out social-preview.png`
- Claude plugin validation: `claude plugin validate .`
- VS Code package: `./scripts/package-vscode.sh`

## Critical rules for working in this repo

### 1. Distinguish user-decision territory from delegated-design territory

The user has been explicit about which decisions are theirs and which are delegated.

- **User-decision territory** (do NOT decide autonomously — these belong in `SPEC.md` under "사용자 결정 대기 항목"):
  - Character name
  - Which of the 4 modes to build first (MVP scope)
  - Timelines and milestones
  - Release channels
  - Success metrics
  - Monetization model and timing (deferred until traffic data exists)
  - Which commercial tracks to launch: direct-purchase packs, creator marketplace, team edition, brand collaborations, physical goods

- **Delegated design territory** (the user explicitly said "디자인은 너가 출처들 조합해서"):
  - Character proportions, expressions, motions
  - Sound library and ASMR mapping
  - Color palette
  - Typography
  - UI visual tone

If unsure whether something is delegated, treat it as user-decision and ask.

### 2. Do not import patterns from other projects without being asked

There is a precedent in this session: a `PROCESS.md` was first written using the 5-stage validation pattern from another project (`ap-csa-book/`). The user pushed back: "근데 이거는 전혀 연관이 없는데 왜 나는 이거 MCP 캐릭터만 만들라고 했잖아." The pattern was removed.

**Do not assume the user wants patterns from `ap-csa-book/` or any other project applied here.** Build the process from what the user has stated for this project.

### 3. The 4 user-stated requirements are non-negotiable

From `SPEC.md`:
1. MCP server registrable form
2. GitHub one-line install (Claude Code / Codex)
3. CPU·battery system info displayed
4. Character has personality (not a plain notifier)
5. Korean trends (artisan keycap + slime ASMR) reflected with explicit sources
6. "New but familiar" design — informed by TikTok/YouTube high-view sounds/motions/styles
7. Design delegated to Claude

Any feature added that doesn't trace to one of these should be flagged as an additional decision, not assumed.

### 4. Sources must be explicit

The user requested "출처 명확하게" (sources explicit). When the design or feature references a trend, cite the source URL in the relevant doc. The current source list lives at the bottom of `SPEC.md`.

### 5. The four modes are all free (jointly decided)

Pet / Notification / Widget / VTuber — all four modes are free in the base product. Any gating logic must respect this.

Monetization, if introduced, will be **post-traffic** and **not by gating modes**. Commercial expansion should prefer direct-purchase packs, creator packs, team support, signed/offline bundles, collaborations, and physical goods before any paid random reward. No implementation until the user decides.

### 6. Cross-platform from day one

Tauri or Electron — jointly decided. Linux/macOS/Windows must all work. Avoid Linux-only or macOS-only paths.

## Working flow (from PROCESS.md)

- **Step A** — converge user decisions (mostly complete as of 2026-05-18; character name decided as tteoki)
- **Step B** — MCP server core (`server/`, Python, FastMCP). Build the **common core for all four modes**, even though only pet mode will get a client in MVP.
- **Step C** — pet-mode desktop client (`desktop/`, Tauri/Electron). MVP scope: **pet mode only**.
- **Step D** — packaging (npm/PyPI + GitHub Releases per-OS installers)
- **Step E** — GitHub Public Release. Other channels (ProductHunt, HN, Korean communities) are post-traffic decisions.
- **Step F** — commercial expansion track. Strategy only until the user approves specific monetization or partnership moves.
- **Step G** — GitHub star growth track. README/community/social-preview/topics work that improves public launch readiness.

## Step A decisions (2026-05-18)

| Item | Decision |
|---|---|
| MVP scope | Common core for all 4 modes + pet-mode client only |
| Pacing | Free-paced, no deadlines |
| Release channel | GitHub Public Release (others deferred) |
| Character name | **tteoki** (떡이) — Korean rice cake + diminutive suffix "이" |
| Character shape concept | **Korean rice cake (떡) variety series** — design-friendly varieties all included |
| Base character | **가래떡 (garaetteok / Korean rice cake stick)** — horizontal cylinder. Surface 조청 drip animation. **Lengthen-and-slice motion as time visualization** (key novel feature). |
| Slice trigger | Every **N Claude tool calls** (default 10, user-configurable). Sliced pieces stack at bottom of screen and fade out. |

**Do not insert deadlines.** The user chose free pacing.

## When to update this file

- After install, test, or build commands change.
- After the user decides any commercial track in `COMMERCIAL_STRATEGY.md`.
- After the GitHub growth plan in `GITHUB_STAR_STRATEGY.md` changes materially.
- After the floating-window architecture or hooks bridge changes.
