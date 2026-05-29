# chibi-mcp — Process

> 작성일: 2026-05-18
> 본 문서는 사용자가 명시·합의한 사항만 기반으로 구성된다.
> 일정·MVP 범위·캐릭터 이름은 Step A에서 결정되었고, 상업화 세부 모델은 아직 사용자 결정 대기 상태다.

---

## 진행 단계

### Step A. 사용자 결정 수렴 ✅ (대부분 완료)

진행 시작 전 사용자가 결정해야 하는 항목.

- **MVP 범위**: 4모드 공통 코어 먼저 + 펫 모드만 클라이언트 ✅
- **일정**: 자유 페이스 (마감일 없음) ✅
- **출시 채널**: GitHub Public Release ✅
- **캐릭터 이름**: chibi ✅

> Step A의 핵심 결정은 완료. 이후 새 상업화 모델은 별도 사용자 결정으로 다룬다.

### Step B. 코어 — 4모드 공통 인프라 (자유 페이스)

본인이 결정한 MVP 범위: **4모드 공통 코어 먼저**.

- `server/` Python MCP 서버 (FastMCP)
- psutil로 CPU·RAM·배터리·세션 정보 수집
- MCP tools: 캐릭터성 기반 설계 (`get_pet_state`, `pet_say` 등)
- WebSocket 서버 (localhost) — 4모드 클라이언트 모두 호환 가능한 공통 프로토콜
- `claude mcp add chibi -- ...` 한 줄 설치 검증

### Step C. 펫 모드 클라이언트 (Tauri 앱)

MVP는 펫 모드만. 나머지 3모드는 v0.2 이후.

- `desktop/` Tauri 프로젝트
- 펫 모드 윈도우 (transparent + always-on-top)
- [CHARACTER_DESIGN.md](CHARACTER_DESIGN.md) 디자인 적용 (7상태·6모션·7사운드)
- [STYLE_GUIDE.md](STYLE_GUIDE.md) 시각 톤 적용
- 4모드 공통 코어와 WebSocket 통신

### Step D. 패키징 + GitHub Public Release 준비

- `server/`를 GitHub 기반 `pipx install` 경로로 배포 (한 줄 설치 요구사항)
- PyPI 배포는 선택 사항이며, repo variable `PUBLISH_PYPI=true` 설정 후 진행
- `desktop/` Tauri 빌드로 OS별 인스톨러 (Linux .deb / macOS .dmg / Windows .exe)
- `vscode-ext/`를 GitHub Release용 `.vsix`로 패키징
- GitHub Actions로 3-OS 자동 빌드
- 첫 실행 UX (사운드 동의 모달 등) — Step C/D 진행 중 사용자 결정 요청

### Step E. GitHub Public Release + 트래픽 수집

- GitHub Releases v0.1.0 태그 + 인스톨러 3종
- README + 데모 GIF
- 사용자 결정: 추가 채널(ProductHunt·HN·한국 커뮤니티) 시점

이후:
- 트래픽 수집 → 사용자가 v0.2 (알림/위젯/VTuber 추가) 진행 결정
- 트래픽 수집 → 사용자가 유료화 모델 결정 ("트래픽 쌓이면 결정")

### Step F. 상업 확장 트랙 (사용자 결정 후)

사용자 요청(2026-05-29): 아이디어 자체를 더 상업적으로, 더 다양하게 강화.

기본 원칙:

- Pet / Notification / Widget / VTuber 네 모드는 무료 유지
- MCP 기본 도구, 시스템 상태 표시, 로컬 상태 저장은 무료 유지
- 유료화는 기능 잠금이 아니라 콘텐츠, 배포 편의, 팀 지원, 콜라보, 물리 굿즈 중심으로 검토

후보 단계:

- Share loop: 1080x1080 공유 카드, "오늘 N milestones", 데모 GIF
- Content loop: 월간 무료 drop, 직접 구매 캐릭터팩, pack validator
- Creator loop: 외부 작가 pack 제출, 검수 기준, 수익 배분 후보
- Team loop: 조직용 install guide, signed/offline bundle, 팀 전용 pack, 지원
- Partnership loop: 아티잔 키캡, 해커톤/컨퍼런스, 코딩 스트리머 overlay, 굿즈

상세 전략: [COMMERCIAL_STRATEGY.md](COMMERCIAL_STRATEGY.md).

### Step G. GitHub star 성장 트랙

사용자 요청(2026-05-29): 요즘 출처에 맞춰 사람들이 선호하고 GitHub star를 많이 받을만한 형태로 강화.

출시 전 repo 표면:

- README 첫 화면에 no telemetry, one-command install, Claude/Codex/VS Code 지원, share loop 표시
- `GITHUB_STAR_STRATEGY.md`로 최신 출처 기반 star 전략 문서화
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` 추가
- bug/install/character-pack/showcase issue form 추가
- PR template 추가
- GitHub topics와 social preview는 repo settings에서 수동 설정

상세 전략: [GITHUB_STAR_STRATEGY.md](GITHUB_STAR_STRATEGY.md).

---

## 미결정 사항 (사용자 영역)

- v0.2 이후 모드 추가 순서
- 가챠/Drop 도입 시점·방식
- 한국 vs 글로벌 마케팅 비중
- 첫 실행 사운드 동의 UX 디테일 (Step C/D에서 결정 요청 예정)
- 직접 구매 character pack 도입 여부
- creator marketplace / 수익 배분 도입 여부
- team edition / paid support 도입 여부
- 브랜드 콜라보 및 물리 굿즈 우선순위
- GitHub Discussions 활성화 시점
- public launch용 demo GIF/social preview 제작 순서
