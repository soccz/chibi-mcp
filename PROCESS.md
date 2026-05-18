# chibi-mcp — Process

> 작성일: 2026-05-18
> 본 문서는 사용자가 명시·합의한 사항만 기반으로 구성된다.
> 일정·MVP 범위·캐릭터 이름 등은 `[미정]`이며 사용자가 결정하면 채워진다.

---

## 진행 단계

### Step A. 사용자 결정 수렴 ✅ (대부분 완료)

진행 시작 전 사용자가 결정해야 하는 항목.

- **MVP 범위**: 4모드 공통 코어 먼저 + 펫 모드만 클라이언트 ✅
- **일정**: 자유 페이스 (마감일 없음) ✅
- **출시 채널**: GitHub Public Release ✅
- **캐릭터 이름**: 진행 중 (3개 후보 검토)

> 캐릭터 이름 확정되면 Step B 진입.

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

- `server/`를 npm/PyPI 배포 (한 줄 설치 요구사항)
- `desktop/` Tauri 빌드로 OS별 인스톨러 (Linux .deb / macOS .dmg / Windows .exe)
- GitHub Actions로 3-OS 자동 빌드
- 첫 실행 UX (사운드 동의 모달 등) — Step C/D 진행 중 사용자 결정 요청

### Step E. GitHub Public Release + 트래픽 수집

- GitHub Releases v0.1.0 태그 + 인스톨러 3종
- README + 데모 GIF
- 사용자 결정: 추가 채널(ProductHunt·HN·한국 커뮤니티) 시점

이후:
- 트래픽 수집 → 사용자가 v0.2 (알림/위젯/VTuber 추가) 진행 결정
- 트래픽 수집 → 사용자가 유료화 모델 결정 ("트래픽 쌓이면 결정")

---

## 미결정 사항 (사용자 영역)

- v0.2 이후 모드 추가 순서
- 가챠/Drop 도입 시점·방식
- 한국 vs 글로벌 마케팅 비중
- 첫 실행 사운드 동의 UX 디테일 (Step C/D에서 결정 요청 예정)
