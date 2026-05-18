# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`chibi-mcp` is an MCP server + cross-platform desktop character ("chibi") that surfaces system state (CPU, battery, session) through a character with personality. It is installed via the standard MCP install path (`claude mcp add ...`) and runs the character as a separate desktop app that talks to the MCP server over localhost.

The project is in **pre-code planning**: only specification documents exist. No code in `server/`, `desktop/`, `characters/`, or `build/` yet.

## Repository structure (planning phase)

- `SPEC.md` — the source of truth for **what the user has actually asked for** and **what was jointly decided** vs **what is still undecided**. Read this first.
- `CHARACTER_DESIGN.md` — character specifications (proportions, expressions, motions, sounds, palette). This is the **delegated design domain** (the user explicitly delegated design to Claude).
- `STYLE_GUIDE.md` — UI, typography, voice, share-card design. Also delegated design domain.
- `PROCESS.md` — Step A through Step E. Step A is gated on user decisions and **must complete before Step B**.
- `server/` — future Python MCP server (FastMCP). Empty.
- `desktop/` — future Tauri/Electron app. Empty.
- `characters/` — future character sprites/SVG/Lottie assets. Empty.

When the project leaves the planning phase, this file should be updated with the actual build/test/run commands for `server/` and `desktop/`.

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

Monetization, if introduced, will be **post-traffic** and **not by gating modes**. Gacha-style mechanics were discussed; the leading model under consideration is the Korean keycap "raffle / monthly drop" pattern (transparent pricing, published probabilities) to stay within Korean game-industry-act compliance — but no implementation until the user decides.

### 6. Cross-platform from day one

Tauri or Electron — jointly decided. Linux/macOS/Windows must all work. Avoid Linux-only or macOS-only paths.

## Working flow (from PROCESS.md)

- **Step A** — converge user decisions (mostly complete as of 2026-05-18; character name still pending)
- **Step B** — MCP server core (`server/`, Python, FastMCP). Build the **common core for all four modes**, even though only pet mode will get a client in MVP.
- **Step C** — pet-mode desktop client (`desktop/`, Tauri/Electron). MVP scope: **pet mode only**.
- **Step D** — packaging (npm/PyPI + GitHub Releases per-OS installers)
- **Step E** — GitHub Public Release. Other channels (ProductHunt, HN, Korean communities) are post-traffic decisions.

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

- After Step A completes (the undecided items in `SPEC.md` will become decided — reflect them here in a "Decisions" section).
- After `server/` gets its first commit (add the install/run/test commands).
- After `desktop/` gets its first commit (add the Tauri/Electron dev/build commands).
