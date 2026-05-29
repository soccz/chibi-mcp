# chibi-mcp — Commercial Expansion Strategy

> 작성일: 2026-05-29
> 목표: Claude Code / Codex / VS Code에서 바로 설치되는 개발자 캐릭터 펫을, 무료 코어를 유지하면서 상업적으로 확장 가능한 제품으로 만든다.

---

## Commercial Thesis

`chibi-mcp`는 단순 데스크탑 펫이 아니라 **AI coding companion identity layer**다.

개발자는 이미 Claude Code, Codex, VS Code 안에서 장시간 머문다. chibi는 그 작업 흐름 안에 들어가서 시스템 상태, 세션 리듬, 도구 호출, 컬렉션, 공유 가능한 캐릭터성을 붙인다. 지금 단계의 목표는 결제 기능이 아니라 다음 네 가지 장기 확장 기반을 무료 코어 위에 준비하는 것이다.

1. **수집 가능한 캐릭터 콘텐츠**
2. **팀/조직용 배포와 관리**
3. **브랜드·크리에이터 콜라보**
4. **물리 굿즈와 개발자 책상 문화**

기존 결정 유지:

- Pet / Notification / Widget / VTuber 네 모드는 기본 무료.
- CPU/RAM/BAT/idle 표시와 MCP 도구는 무료 코어.
- **아직 유료화하지 않는다.** 가격, 결제, Sponsors, revenue share, 유료 pack, 유료 team edition은 사용자가 명시 승인하기 전까지 구현하지 않는다.
- 사업성 문서는 **준비와 검증**만 다룬다: pack schema, 샘플팩, 배포 경로, 신뢰 문서, 런칭 자료.

---

## Commercial Readiness Surfaces

상업적으로 부족한 부분은 기능 수가 아니라 **도입 이유, 반복 사용 증거, 팀 검토 흐름, 파일럿 피드백 루프**다. 결제 기능 없이 다음 표면을 먼저 강화한다.

- [docs/PRODUCT_MARKET_READINESS.md](docs/PRODUCT_MARKET_READINESS.md): 타깃 사용자, 부족한 증거, 유료화 전 readiness gate.
- [docs/TEAM_ADOPTION.md](docs/TEAM_ADOPTION.md): 팀/admin 평가 질문, `chibi-audit --json`, 배포 경로, team pack 검토.
- [docs/PILOT_PLAYBOOK.md](docs/PILOT_PLAYBOOK.md): 무료 파일럿 질문, 성공 신호, telemetry 없는 측정 방식.
- `.github/ISSUE_TEMPLATE/team_pilot.yml`: 팀/파일럿 피드백 수집.
- `.github/ISSUE_TEMPLATE/collaboration_idea.yml`: 무료 drop, creator/community pack, hackathon/keycap/devtool 협업 제안 수집.
- `chibi-audit`: trust report에 commercial readiness 문서와 파일럿/협업 템플릿 누락 여부를 표시.

이 표면들은 유료화가 아니라 **나중에 돈을 받을 수 있는 이유가 실제로 있는지 검증**하기 위한 장치다.

---

## Product Surfaces

### 1. Free Core

목적: GitHub star, 설치 수, 공유 카드, 커뮤니티 확산.

- GitHub 직접 설치
- Claude Code plugin marketplace
- Codex plugin marketplace
- VS Code `.vsix`
- 8개 starter character
- 하루 무료 뽑기
- 로컬-only 상태 저장
- telemetry 없음
- `chibi-mcp --check`로 설치 진단
- `chibi-audit`로 로컬 신뢰 리포트 출력
- `chibi-share`로 1080×1080 세션 공유 카드 생성
- `chibi-share --preset lineup`으로 제공된 PNG 캐릭터 전체 라인업 생성
- `chibi-share --preset options`로 앰버 글레이즈·꿀·비즈·가루·씨앗·꽃잎·레진·소스 12종 옵션 쇼케이스 생성
- `chibi-pack validate/preview`로 크리에이터·팀 캐릭터팩 검증
- `examples/packs/spring-hwajeon`, `examples/packs/team-sprint`로 실제 검증 가능한 creator/team pack 템플릿 제공
- `docs/CREATOR_PACKS.md`, `docs/LAUNCH_KIT.md`로 제출/배포/런칭 루프 문서화
- `docs/PRODUCT_MARKET_READINESS.md`, `docs/TEAM_ADOPTION.md`, `docs/PILOT_PLAYBOOK.md`로 타깃/팀/파일럿 검증 루프 문서화

무료 코어는 줄이지 않는다. 이 제품은 신뢰와 귀여움이 먼저다.

### 2. Character Drops

목적: 반복 방문과 공유.

현재 drop은 무료 중심으로 운영한다. paid random reward는 규제와 신뢰 리스크가 있으므로 도입하지 않는다.

권장 모델:

- Monthly free drop: 매월 1종 무료 공개
- Monthly free option: 앰버 글레이즈/꿀/비즈/스프링클/콩가루/흑임자/꽃잎/레진 별 같은 작은 옵션 레이어 공개
- Free creator/community pack: 작가·기여자가 제안한 pack을 무료 검토/공개
- Limited collab drop: 기간 한정 브랜드/작가 콜라보 후보 검토
- Contributor drop: 오픈소스 기여자 전용 배지/캐릭터
- Event drop: GitHub release, hackathon, conference 참여 보상

피해야 할 것:

- 유료 확률형 가챠를 바로 도입
- 모드 기능을 잠그는 Pro
- 유료 pack, Sponsorship tier, creator revenue share를 지금 구현
- 사용자 몰래 telemetry 기반 보상 설계

### 3. Creator Marketplace

목적: 콘텐츠 생산량을 외부로 확장.

구조:

- 공식 캐릭터/옵션 메타 스키마 공개
- PNG pack + `meta.json` validator 제공
- 작가별 pack을 GitHub Release나 웹 카탈로그로 배포
- 수익 배분/판매는 지금 정하지 않는다. 현재는 무료 제출·검수·preview 흐름만 만든다.
- 검수 기준: 투명 배경 PNG, 128/256/512, `license`와 `source_rights`, 저작권 확인, NSFW 금지

MVP:

- `chibi-pack validate <dir>` CLI
- `chibi-pack validate --submission <dir>` rights gate
- pack preview HTML
- GitHub issue template: character pack submission

현재 실행 가능한 기반:

```bash
chibi-pack init ./my-pack
chibi-pack validate ./my-pack
chibi-pack validate --submission ./my-pack
chibi-pack preview ./my-pack
chibi-pack validate --submission examples/packs/spring-hwajeon
chibi-pack validate --submission examples/packs/team-sprint
```

`meta.json`의 `characters[]` 항목은 `id`, `name_ko`, `category`, `rarity`, `tier`, PNG 이미지로 검증된다. `options[]` 항목은 `id`, `name_ko`, `category`, `tier`, PNG 이미지로 검증된다. 이 단계는 marketplace 결제를 켜기 전에도 작가·팀·브랜드 pack 품질을 표준화한다.

### 4. Team Edition

목적: 유료 team edition이 아니라, 팀이 안심하고 설치를 검토할 수 있는 배포·관리 기반을 준비한다.

팀 기능은 개인 재미와 다르게 “관리·배포·통제”가 가치다.

- 팀 전용 character pack
- 조직 로고/프로젝트별 mascot skin
- admin-approved marketplace config
- signed releases / checksums
- offline install bundle
- no-telemetry audit note
- priority support
- team share cards: sprint milestone, PR milestone, release milestone

현재 실행 가능한 기반:

```bash
chibi-audit --json
chibi-share --out sprint-card.png
chibi-share --preset social-preview --out social-preview.png
chibi-share --preset lineup --out starter-lineup.png
chibi-share --preset options --out option-showcase.png
```

팀 배포 검토 전에는 이 두 결과물을 readiness asset으로 쓴다. `chibi-audit`는 no telemetry, localhost-only default, state path, asset catalog, hook/plugin files를 보여주고, `chibi-share`는 팀/스프린트/릴리스 공유 카드의 초기 형태가 된다.

가격 후보는 아직 만들지 않는다. 가격표, 라이선스 키, entitlement, 결제 페이지, 유료 support tier는 모두 명시 승인 전 금지다. 이 문서에서 "Team Edition"은 당분간 유료 제품명이 아니라 팀 설치 검토용 준비 영역을 뜻한다.

### 5. Brand Collaborations

목적: 개발자 문화와 책상 문화를 연결.

적합한 브랜드:

- artisan keycap makers
- mechanical keyboard shops
- indie devtools
- hackathon/conference organizers
- Korean stationery/cafe/productivity brands
- VTuber/streamer coding channels

상품 형태:

- “키캡 캐릭터 + MCP skin” 세트
- conference badge character
- seasonal collaboration character
- open-source maintainer 감사 drop
- livestream overlay pack

브랜드 콜라보 원칙:

- 코어 UX에 광고를 넣지 않는다.
- 협찬/스폰서 표기는 아직 도입하지 않는다. 나중에 승인되더라도 캐릭터 설명/카탈로그에만 두고 workflow에는 끼워 넣지 않는다.
- collab character도 사용자가 직접 선택해야 보인다.

### 6. Physical Goods

목적: 디지털 캐릭터를 책상 문화로 확장.

후보:

- chibi sticker pack
- desk mat
- artisan keycap
- acrylic stand
- plush
- “오늘 N milestones” calendar card
- small chibi-themed desk toy

물리 굿즈는 지금 판매하지 않는다. 장기적으로 검토할 수 있는 커뮤니티 정체성 후보로만 둔다.

---

## Feature Expansion Ideas

### GitHub Star Loop

목적: 설치 수보다 먼저 "보고 싶고 공유하고 싶은 repo"가 되게 만든다.

- README 첫 10초 안에 one-command install, no telemetry, Claude/Codex/VS Code, slice/gacha가 보이게 한다.
- GitHub social preview는 1280x640 이미지로 만든다.
- repo topics는 `mcp`, `model-context-protocol`, `claude-code`, `codex`, `vscode-extension`, `local-first`, `no-telemetry`, `desktop-pet`, `ai-agent` 중심으로 설정한다.
- issue templates는 bug/install/character-pack/showcase로 나눠 사용자 행동을 "문제 보고"뿐 아니라 "공유"와 "캐릭터 제안"으로 유도한다.
- paid-looking unlock 대신 월간 무료 drop과 contributor badge로 첫 커뮤니티 루프를 만든다.
- GitHub Traffic의 14일 referrer/popular-content를 보고 README, demo GIF, install docs를 계속 고친다.

상세 전략: [GITHUB_STAR_STRATEGY.md](GITHUB_STAR_STRATEGY.md).

### Developer Rituals

- “첫 커밋 milestone”
- “CI 실패하면 시무룩”
- “release tag 만들면 반짝”
- “PR merge milestone”
- “야근 감지 졸림”

### Shareable Artifacts

- 1080×1080 share card
- GitHub README badge: `chibi worked with me N calls`
- release celebration card
- team sprint recap image
- VS Code sidebar screenshot card

### Multi-Client Modes

- Claude Code: `/chibi` 중심, pet + gacha + inventory
- Codex: MCP tools + plugin marketplace
- VS Code: sidebar collection + native view
- Terminal-only: ASCII/PNG status fallback for SSH users
- Stream overlay: transparent browser source for coding streams

### Privacy-First Analytics

Telemetry 없음은 유지한다. 대신 사용자가 직접 내보내는 방식으로 측정한다.

- local `chibi-mcp stats export`
- opt-in share card
- GitHub release download count
- GitHub stars/issues/discussions
- VSIX download count if Marketplace publish happens later

---

## Commercial Roadmap

### Phase 0 — Trust and Installability

Already in progress.

- GitHub install scripts
- `chibi-mcp --check`
- Claude plugin validation
- Codex plugin validation
- VS Code `.vsix`
- no telemetry statement
- security/trust notes

Stopping condition:

- A new user can install, run `/chibi`, and see a pet window or a clear `tkinter`/desktop-session diagnostic.

### Phase 1 — Share Loop

Build before payment.

- share card generator
- “오늘 N milestones” visual
- GitHub issue template for sharing pets
- demo GIF in README
- starter pack polish

Success signal:

- people post screenshots without being asked.

### Phase 2 — Content Loop

- monthly drop schedule
- pack schema and validator
- creator submission flow
- free creator/community pack submissions
- contributor badge / contributor cosmetic

Success signal:

- users ask for a specific character or submit their own pack.

### Phase 3 — Team Loop

- team install guide
- admin marketplace config example
- signed release checksums
- team pack
- offline install bundle

Success signal:

- teams ask “how do we install this for everyone?” rather than “what is this?”

### Phase 4 — Partnerships

- artisan keycap collab
- hackathon badge character
- conference drop
- coding streamer overlay
- limited free collaboration pack

Success signal:

- partner brings distribution, not only money.

---

## Risks and Guardrails

| Risk | Guardrail |
|---|---|
| MCP/plugin trust concerns | keep source open, no telemetry, clear `--check`, signed releases later |
| Paid gacha regulation/trust risk | do not implement paid gacha; keep drops free until explicit approval |
| Too many clients, shallow product | Claude Code remains primary; Codex/VS Code are distribution surfaces |
| Cute but not useful | keep system state, calls, slices, CI/dev rituals visible |
| Artist content quality variance | pack validator + visual review checklist |
| Copycat or unclear asset rights | `ASSET_RIGHTS.md`, source/provenance metadata, `chibi-pack validate --submission`, DMCA evidence checklist |
| Brand collab feels like ads | no sponsor placement for now; future credit only in catalog/share card if approved |

---

## Decisions Needed Later

These remain user/business decisions, not implementation assumptions:

- Whether to ever sell direct-purchase character packs
- Whether to publish on VS Code Marketplace or keep GitHub Release `.vsix`
- Whether to allow creator revenue share
- Whether to create paid team support
- Whether to ever introduce paid random pulls
- Which brand/category to approach first
- Whether to create a public website beyond GitHub

---

## Source Notes

- Claude Code plugins are distributed through marketplaces; GitHub repos with `.claude-plugin/marketplace.json` can be added with `owner/repo`, and plugins can include skills, commands, hooks, and MCP servers: https://code.claude.com/docs/en/discover-plugins
- Claude Code plugin docs explicitly warn that marketplaces/plugins are trusted components that can execute code, so commercial packaging must emphasize trust and review: https://code.claude.com/docs/en/discover-plugins
- VS Code supports installing `.vsix` extensions via the `code --install-extension <extension-vsix-path>` command: https://code.visualstudio.com/docs/configure/extensions/extension-marketplace
- VS Code extension docs describe `vsce package` producing installable `.vsix` files, including private/GitHub-release distribution: https://code.visualstudio.com/api/working-with-extensions/publishing-extension
- Open VSX is an open-source registry for VS Code-compatible editors, and its publishing guide documents `ovsx publish <file> -p <token>` for `.vsix` distribution: https://open-vsx.org/about, https://github.com/eclipse/openvsx/wiki/Publishing-Extensions
- GitHub Sponsors supports one-time and monthly sponsorship tiers for open-source maintainers; chibi-mcp should not enable it until the user explicitly approves monetization: https://docs.github.com/en/sponsors/getting-started-with-github-sponsors/about-github-sponsors
- GitHub Octoverse 2025 reports rapid AI project and agentic-workflow growth, which supports positioning chibi-mcp as an AI coding companion rather than a generic desktop toy: https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/
- GitHub docs recommend topics for discovery, community health files, issue/PR templates, social preview images, and Traffic insights for repository growth loops: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics
