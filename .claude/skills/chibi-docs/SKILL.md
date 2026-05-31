---
name: chibi-docs
description: chibi-mcp 문서 지형과 규약 — SPEC.md 결정 로그 작성법, chibi 브랜딩 카피 규칙, 출처 명시, 위임설계(CHARACTER_DESIGN/STYLE_GUIDE) vs 사용자결정 경계, README 필수 신호. chibi-docs-keeper가 문서/SPEC/CHANGELOG/설계문서를 갱신할 때 사용. 기능 변경이 문서에 반영되어야 하거나 결정 사항을 기록할 때 반드시 적용.
---

# chibi-docs — 문서 지형 · 작성 규약

## 문서 지형 (무엇이 어디에)

| 분류 | 파일 | 갱신 권한 |
|------|------|----------|
| **정본 (truth)** | `SPEC.md`(요구·결정·미결·출처), `PROCESS.md`(Step A~G) | 사용자 결정만 기록 — 임의 결정 금지 |
| **위임 설계** | `CHARACTER_DESIGN.md`(비율·표정7·모션·사운드·팔레트·변형시리즈), `STYLE_GUIDE.md`(타이포·보이스·로고·UI·공유카드) | 자율 작성 가능 |
| **상업** | `COMMERCIAL_STRATEGY.md`, `docs/PRODUCT_MARKET_READINESS.md`, `docs/TEAM_ADOPTION.md`, `docs/PILOT_PLAYBOOK.md`, `docs/CREATOR_PACKS.md`, `docs/LAUNCH_KIT.md` | 전략·준비도만, 수익화 구현 금지 |
| **GitHub 성장** | `GITHUB_STAR_STRATEGY.md` | 자율 |
| **권리/IP** | `ASSET_RIGHTS.md`, `OFFICIAL_ASSET_TERMS.md`, `TRADEMARK.md`, `docs/IP_AND_RIGHTS.md`, `docs/COPYCAT_RESPONSE.md` | 출처·권리 메타데이터 |
| **커뮤니티** | `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/` | 자율 |
| **설치/릴리스** | `INSTALL.md`, `docs/TROUBLESHOOTING.md`, `docs/RELEASE_PROCESS.md`, `docs/PUBLIC_BETA_READINESS.md`, `CHANGELOG.md` | 코드와 일치 |
| **공개 첫인상** | `README.md` | 필수 신호 유지(아래) |
| **미래 모드** | `SPEC_V0.2.md`(알림/위젯/VTuber) | 사용자 결정 후 |

## SPEC.md 결정 로그 규약

- **새 사용자 결정**이 내려지면 → "같이 결정한 사항" 표 또는 "Step A 결정사항" 표에 **날짜와 함께** 추가. 상대 날짜는 절대 날짜로 변환(오늘 = 2026-05-31).
- **미결 항목** → "아직 사용자 결정 대기" 표에 상태 표기(`[미정 — ...]`).
- SPEC은 "사용자가 직접/함께 결정한 사항만 기록"하는 문서다. 추측·제안을 결정인 양 적지 않는다.
- 새 요구사항이 들어오면 "사용자가 명시한 요구사항" 번호 목록에 날짜를 달아 추가.

## chibi 브랜딩 카피 규칙 (2026-05-30 결정)

- **공개 표면은 전부 chibi.** README, 스크린샷, 공유/소셜 카드, 마켓플레이스·플러그인 메타, 인스톨러 텍스트, 런타임 UI.
- 이전 음식·시럽 계열 캐릭터명을 공개 표면에 **쓰지 않는다.** 레거시 내부 ID/파일명은 호환 세부로만 남고, 생성되는 README/자산에 누설 금지.
- `verify_all.sh` 5단계가 레포 전체에서 금칙 브랜드 용어를 스캔하고 카탈로그 `meta.json` 표시 필드도 검사한다. 문서에 레거시 표시명을 넣으면 게이트가 깨진다.
- 단, `characters/characters_meta.json`의 실제 한글명(흰떡·모찌 등)은 설계 마스터의 내부 데이터다 — 공개 카피로 끌어오지 않는다.

## 출처 명시 규칙

- 트렌드·디자인 근거를 인용하면 URL 출처를 단다. SPEC.md 하단 "출처" 섹션이 마스터 목록(아티잔 키캡, 슬라임 ASMR, chibi 디자인, 마스코트 트렌드, 저작권/상표). 새 근거는 해당 카테고리에 URL과 한 줄 설명으로 추가.

## README 필수 신호 (public-beta preflight가 검사)

`public_beta_preflight.sh`가 README에 다음 문자열 존재를 강제한다 — 약화/삭제 금지:
- "no telemetry"
- "Monetization is not enabled"
- 클라이언트 이름(Claude Code / Codex / VS Code)
- `chibi-mcp --check`

또한 4모드가 전부 무료라는 표현, one-command install을 유지한다.

## 위임설계 vs 사용자결정 (문서 작성 시)

- CHARACTER_DESIGN/STYLE_GUIDE의 시각·청각·톤 디테일은 자율. 단 거기에 **이름·MVP범위·일정·채널·지표·수익화** 같은 사용자 결정 항목을 못 박지 않는다.
- 불확실하면 SPEC에 결정으로 적지 말고 리더에 회부(guardian 판단).

## 버전 문자열 분담

README/INSTALL의 `1.4.39`는 surface-sync의 드리프트 맵에도 있다. 리더가 누가 갱신할지 정한다 — 중복 편집으로 충돌내지 않는다. 기본적으로 버전 숫자 자체는 surface-sync, 설명 문맥은 docs-keeper.

## 산출물 형식

`_workspace/04_docs_report.md`: 갱신한 문서 목록, SPEC에 추가한 결정/미결 항목, 브랜딩·출처·README필수신호 점검 결과.
