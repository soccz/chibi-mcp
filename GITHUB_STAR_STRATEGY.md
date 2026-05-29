# chibi-mcp — GitHub Star Strategy

> 작성일: 2026-05-29
> 목표: 최신 AI coding / MCP / GitHub 오픈소스 흐름에 맞춰, 사람들이 바로 이해하고 설치하고 공유하고 star를 누를 이유가 있는 repo로 만든다.

---

## Thesis

`chibi-mcp`가 star를 받을 수 있는 이유는 "귀여운 캐릭터"만이 아니다. 더 강한 포지션은 다음이다.

> **The cutest local MCP companion for AI coding sessions.**

이 포지션은 세 가지 최신 흐름에 맞다.

1. **AI coding이 기본값이 됨** — GitHub Octoverse 2025는 AI 프로젝트와 agentic workflow가 빠르게 늘고 있음을 보여준다.
2. **MCP가 AI-native tooling 표면이 됨** — GitHub Copilot/VS Code 팀도 MCP 기반 오픈소스 프로젝트를 후원하며 에디터·브라우저·툴 통합을 강조했다.
3. **오픈소스 선택은 신뢰 신호가 중요함** — MCP/plugin은 로컬 코드를 실행할 수 있으므로, no telemetry, `--check`, SECURITY, 커뮤니티 파일, 명확한 설치 경로가 star 전환에 직접 영향을 준다.

---

## Star-Worthy Shape

### 1. First 10 Seconds

방문자가 첫 화면에서 바로 봐야 하는 것:

- what it is: local MCP pet for Claude Code / Codex / VS Code
- why it is fun: coding session reacts, slice cycle, gacha collection
- why it is safe: no telemetry, localhost, open source, `chibi-mcp --check`
- how to try: one-command install
- why to star: monthly drops, creator packs, VS Code builds, roadmap

README 첫 화면은 설명서보다 데모 판매 페이지처럼 작동해야 한다. 단, 과장된 마케팅 페이지가 아니라 "개발자가 30초 안에 설치할 수 있는 repo"여야 한다.

### 2. Demo-First Assets

Star conversion에 필요한 시각 자료:

- README 상단 GIF: pet opens, mood changes, slice drops
- 1280x640 GitHub social preview image
- 1080x1080 share card: "오늘 7도막 잘림"
- 1600x900 starter lineup generated from the project PNG assets
- 1600x900 option showcase generated from 12 free topping/glaze/powder/seed/resin PNG layers
- runnable creator/team pack examples under `examples/packs/`
- VS Code sidebar screenshot
- Claude Code `/chibi` screenshot
- Codex terminal screenshot

우선순위:

1. `assets/social-preview.png`
2. `docs/screenshots/starter-lineup.png`
3. `docs/screenshots/option-showcase.png`
4. `docs/LAUNCH_KIT.md`
5. `docs/CREATOR_PACKS.md`
6. `docs/demo.gif`
7. `docs/screenshots/claude-code.png`
8. `docs/screenshots/vscode-sidebar.png`

현재 실행 가능한 시작점:

```bash
chibi-share --out docs/screenshots/share-card.png
chibi-share --preset social-preview --out assets/social-preview.png
chibi-share --preset lineup --out docs/screenshots/starter-lineup.png
chibi-share --preset options --out docs/screenshots/option-showcase.png
chibi-pack validate examples/packs/spring-hwajeon
chibi-pack preview examples/packs/spring-hwajeon --out docs/screenshots/pack-preview.html
chibi-pack validate examples/packs/team-sprint
```

실제 demo GIF는 수동 녹화가 필요하지만, share card, social preview, starter lineup, option showcase, pack preview, sample pack validation은 repo 안에서 즉시 실행 가능하다.

### 3. Topics for Discovery

GitHub repository topics should include:

```text
mcp
model-context-protocol
claude-code
codex
vscode-extension
developer-tools
ai-agent
agentic-workflow
local-first
no-telemetry
desktop-pet
python
tauri
open-source
korean
chibi
```

Rationale: topics help people find and contribute to projects by subject area. The repo should sit at the intersection of MCP, AI agent tooling, VS Code, and playful developer tools.

### 4. Community Surface

Files that should exist before public launch:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/install_problem.yml`
- `.github/ISSUE_TEMPLATE/character_pack.yml`
- `.github/ISSUE_TEMPLATE/showcase.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`

Why: GitHub's community profile checks for recommended files, and issue/PR templates standardize the information contributors provide.

### 5. Share Loop

People star projects they want to come back to. chibi-mcp needs repeatable moments:

- "오늘 N도막" daily share card
- "첫 PR merge 도막"
- "CI 실패 시무룩"
- "release tag 반짝"
- "월간 떡 drop"
- "이번 달 옵션 토핑"
- "contributor-only badge"

The first paid-looking feature should not be paid. It should be a shareable, local-only artifact that proves the product is alive.

### 6. Trust Loop

MCP/plugin trust is a growth feature, not only a security feature.

Must stay visible:

- no telemetry statement in README
- `chibi-mcp --check`
- `chibi-audit`
- localhost-only WebSocket default
- SECURITY.md with reporting path
- no hidden paid gate in the open-source core
- no embedded license secret or placeholder production key
- release checksums later

---

## Launch Sequence

### Pre-Launch

- Finish GitHub install paths for Claude Code, Codex, and VS Code.
- Add demo GIF/social preview.
- Add community health files.
- Add GitHub topics.
- Pin a release issue: "Show your tteoki".
- Open Discussions if the repo starts receiving questions.

### Launch

- Tag a GitHub Release with `.vsix`, wheel artifact, and checksums.
- Post a short demo clip, not a long article.
- Lead with: "local MCP pet for Claude Code/Codex/VS Code, no telemetry".
- Ask for screenshots and character ideas, not only stars.

### After Launch

- Use GitHub Traffic for 14-day visitor/referrer/popular-content measurement.
- Track stars per source manually: GitHub, X, HN, ProductHunt, Korean dev communities.
- Convert repeated requests into issue templates or roadmap entries.
- Release one visible drop quickly if the first wave engages.

---

## Product Decisions To Keep Open

These should not be implemented without user approval:

- paid character packs
- creator revenue share
- VS Code Marketplace publishing
- team edition pricing
- physical goods
- paid random pulls

Star strategy can prepare these surfaces, but it should not silently turn them on.

---

## Source Notes

- GitHub Octoverse 2025 reports more than 180M developers, 630M repositories, 4.3M AI projects, and rapid AI/Copilot adoption: https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/
- GitHub Copilot and VS Code teams sponsored MCP projects for AI-native workflows and agentic tooling: https://github.blog/open-source/accelerate-developer-productivity-with-these-9-open-source-ai-and-mcp-projects/
- GitHub topics help people find and contribute to projects by subject area: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics
- GitHub recommends social preview images, ideally 1280x640 for best display: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview
- GitHub community profile checks recommended files such as README, CODE_OF_CONDUCT, LICENSE, CONTRIBUTING, SECURITY, and issue templates: https://docs.github.com/en/enterprise-cloud@latest/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
- GitHub issue forms standardize useful information from contributors: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository
- GitHub Traffic shows clones, visitors, referrers, and popular content for recent launch analysis: https://docs.github.com/en/enterprise-cloud@latest/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository
- Claude Code plugin docs warn users to trust plugins before installing because plugins and MCP servers can execute code: https://code.claude.com/docs/en/discover-plugins
- VS Code Marketplace publishing uses `vsce package` / `vsce publish`, and packaged `.vsix` files can be installed from the command line: https://code.visualstudio.com/api/working-with-extensions/publishing-extension
- Open VSX provides a VS Code-compatible open-source registry and publishing path for `.vsix` packages: https://open-vsx.org/about, https://github.com/eclipse/openvsx/wiki/Publishing-Extensions
