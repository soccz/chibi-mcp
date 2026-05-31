# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`chibi-mcp` is an MCP server + cross-platform desktop character ("chibi") that surfaces system state (CPU, battery, session) through a character with personality. It is installed from GitHub for Claude Code, Codex, and VS Code, and runs a local server/window that talks over localhost where a desktop session is available.

The project now has an executable Python MCP server, Claude/Codex plugin metadata, a VS Code `.vsix` packaging path, and a floating pet window implemented in pure Python (tk + Pillow) spawned as a detached subprocess by the MCP server. PyObjC transparency experiments are opt-in only because Homebrew Python/Tk/PyObjC combinations can crash natively on macOS. A legacy Tauri attempt remains under `desktop/` for v0.1–v0.2 reference but is not part of the current install path. Some docs still describe future product phases; check the current files before assuming a phase boundary.

Branding rule from the 2026-05-30 user decision: public-facing README copy,
screenshots, share cards, marketplace/plugin metadata, installer text, and
runtime UI must use **chibi**. Do not show previous food-specific character
or syrup naming on public surfaces. Legacy internal IDs and filenames may stay
only as compatibility details and must not leak into generated README assets.

## Repository structure

- `SPEC.md` — the source of truth for **what the user has actually asked for** and **what was jointly decided** vs **what is still undecided**. Read this first.
- `CHARACTER_DESIGN.md` — character specifications (proportions, expressions, motions, sounds, palette). This is the **delegated design domain** (the user explicitly delegated design to Claude).
- `STYLE_GUIDE.md` — UI, typography, voice, share-card design. Also delegated design domain.
- `PROCESS.md` — Step A through Step G. Step F/G are commercial and GitHub growth strategy, not approved monetization implementation.
- `COMMERCIAL_STRATEGY.md` — commercial expansion candidates and guardrails.
- `docs/PRODUCT_MARKET_READINESS.md`, `docs/TEAM_ADOPTION.md`, `docs/PILOT_PLAYBOOK.md` — commercial readiness, team evaluation, and free pilot feedback loops without monetization.
- `GITHUB_STAR_STRATEGY.md` — source-backed GitHub growth plan, topics, community surface, launch loop.
- `INSTALL.md` — GitHub install matrix for Claude Code, Codex, and VS Code.
- `docs/TROUBLESHOOTING.md` — user-facing install/runtime fixes and issue checklist.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/` — public community and trust surface.
- `ASSET_RIGHTS.md`, `OFFICIAL_ASSET_TERMS.md`, `TRADEMARK.md`, `docs/IP_AND_RIGHTS.md`, `docs/COPYCAT_RESPONSE.md` — official asset provenance, pack rights, brand/fork naming, and copycat response guardrails.
- `server/` — Python MCP server package. Also ships the floating pet window (`chibi_mcp/window.py`), the `chibi-say` CLI used by hooks, and the `chibi-check` self-diagnostic.
- `hooks/`, `bin/` — Claude Code plugin hooks bridge: `hooks/hooks.json` fires `bin/chibi-react.sh` on PreToolUse / PostToolUse, which forwards a contextual phrase via `chibi-say` to the floating window.
- `scripts/install-*.sh`, `scripts/install-*.ps1` — Linux/macOS bash and Windows PowerShell install paths for Claude Code, Codex, and VS Code.
- `vscode-ext/` — VS Code extension packaging path. As of 0.5.0 also calls `chibi-say` on save / task / debug events.
- `desktop/` — legacy Tauri client; archival only.
- `server-rs/` — Rust MCP prototype (alternative to the Python server). Implements only 4 of the 16 tools (`get_pet_state`, `pet_say`, `slice_now`, `set_slice_interval`); gacha/inventory/window/catalog tools are a parity gap, and it shares the same `ws://127.0.0.1:9876` protocol. `verify_all.sh` lints it (`cargo fmt`/`clippy`). Not on the install path. Porting more tools is a separate decision.
- `assets/` and `server/chibi_mcp/assets/` — starter PNG characters, free option layer PNGs, and metadata.

Core commands:

- Full verification: `make check` or `./scripts/verify_all.sh`
- Python tests: `cd server && python -m pytest -q`
- Server health check: `cd server && python -m chibi_mcp --check`
- Commercial-readiness CLIs: `chibi-audit`, `chibi-pack init/validate/preview <dir>`, `chibi-pack validate --submission <dir>` (requires full rights metadata), `chibi-share --out share-card.png`, `chibi-share --preset social-preview --out social-preview.png`, `chibi-share --preset lineup --out starter-lineup.png`, `chibi-share --preset options --out option-showcase.png`
- Claude plugin validation: `claude plugin validate .`
- VS Code package: `./scripts/package-vscode.sh`
- Release workflow: tagged GitHub Releases attach `SHA256SUMS.txt`; CI also parses Windows PowerShell installers.

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

- **Step A** — converge user decisions (mostly complete as of 2026-05-18; character name updated to chibi on 2026-05-30)
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
| Character name | **chibi** |
| Character shape concept | **chibi variety series** — soft, glossy, collectible starter shapes |
| Base character | **soft horizontal chibi body** with amber/honey gloss options and session-rhythm motion. |
| Milestone trigger | Every **N Claude tool calls** (default 10, user-configurable). chibi plays a small milestone reaction. |

**Do not insert deadlines.** The user chose free pacing.

## 하네스: chibi-mcp 개발

**목표:** 다중 표면 중복(버전·도구·카탈로그·가챠·문구·WS상수)과 엄격한 결정 영역 가드레일을 가진 이 레포에서, 변경이 모든 표면·문서로 일관되게 번지고 사용자 결정 영역을 임의로 건드리지 않도록 5인 에이전트 팀으로 조율한다.

**트리거:** chibi-mcp 코드·문서·배포 변경(기능 추가/버그/리팩터/버전 범프/캐릭터·옵션 추가/표면 동기화/문서 갱신/배포 준비, 그리고 재실행·업데이트·보완) 요청 시 `chibi-dev` 스킬을 사용하라. 단순 질문(코드 위치·동작 설명)은 직접 응답 가능. 런타임 펫 제어(펫 띄워줘/뽑기)는 shipped `skills/chibi` 소관이며 이 하네스 아님.

**구성:** 에이전트 정의는 `.claude/agents/`(guardian·core-dev·surface-sync·docs-keeper·verifier), 스킬은 `.claude/skills/`(chibi-dev 오케스트레이터 + 5개 도메인 스킬). 상세 목록은 그 디렉토리에서 확인.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-05-31 | 초기 구성 (5인 팀 + 6스킬 + 오케스트레이터) | 전체 | 다중 표면 중복·결정 영역 가드레일 대응 |
| 2026-05-31 | 검증 후 보정: verify_all.sh 단계 번호를 실제 16개 배너 섹션으로 재정렬(권리정책 15단계), meta.json byte-identity는 테스트 아닌 diff로 확인하도록 문구 보정, verifier general-purpose 스폰 근거·의미론 명시, docs-keeper 입력 파일명 명시 | chibi-verify, chibi-surface-sync, chibi-verifier, chibi-dev, chibi-docs-keeper | 다차원 적대적 검증 워크플로우(pass_with_minor)가 확정한 문서 정합성 갭 3건 보정 |

## When to update this file

- After install, test, or build commands change.
- After the user decides any commercial track in `COMMERCIAL_STRATEGY.md`.
- After the GitHub growth plan in `GITHUB_STAR_STRATEGY.md` changes materially.
- After the floating-window architecture or hooks bridge changes.
