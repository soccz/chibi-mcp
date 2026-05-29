# chibi-mcp — Style Guide v0.1

> 작성일: 2026-05-18
> 적용 범위: 데스크탑 앱 UI · 웹사이트 (chibi-mcp.dev) · GitHub README · 공유 카드 · 소셜 미디어

---

## 디자인 원칙 5가지

1. **방해 없음** — 캐릭터·UI가 사용자 작업을 가리지 않는다. 항상 위젯 영역만 차지
2. **새롭지만 익숙** — chibi·mochi·슬라임 ASMR이라는 익숙한 코드 + Claude Code 통합이라는 새로움
3. **마이너 정체성** — 인디 감성. 메이저 마스코트(라인프렌즈·카카오프렌즈)와 정반대 톤
4. **수집·자랑** — 사용자가 캐릭터를 자기 정체성 일부로 느끼게. SNS 공유 친화
5. **ASMR 친화** — 모든 인터랙션이 시청각 만족감을 주도록 설계

---

## 타이포그래피

| 용도 | 폰트 | 비고 |
|---|---|---|
| 영문 헤딩 | **Inter** (700) | 모던·중립 |
| 영문 본문 | **Inter** (400) | 가독성 |
| 한글 헤딩 | **Pretendard** (700) | 한국 표준 모던 |
| 한글 본문 | **Pretendard** (400) | 가독성 |
| 캐릭터 말풍선 | **Quicksand** (500) or **나눔손글씨 펜** | 친근·둥근 |
| 코드 | **JetBrains Mono** (400) | 개발자 친화 |

모두 무료/오픈소스. 웹폰트로 로드.

---

## 보이스 톤

### Claude Code 응답 톤
- Claude는 치비를 "설명"하지 말고 "조작 결과"만 짧게 말한다.
- 기본 응답은 한 줄. 사용자가 `/chibi`만 쳤으면 창을 열고 `<이름> ★<희귀도> — <기분>`만 말한다.
- 실패 시에는 원인 + 다음 명령만 준다.
- `get_pet_state` 결과를 그대로 나열하지 않는다. 사용자가 상태를 물어볼 때만 `CPU/RAM/BAT/도막`을 요약한다.

✅ `가래떡(짧) ★★ — 말랑`
✅ `청포도 ★★ 나왔어.`
✅ `오늘 무료뽑기는 썼어. 다음 무료뽑기까지 06:12.`

❌ `MCP 서버에서 WebSocket으로 상태를 브로드캐스트하고 있습니다.`
❌ `현재 mood는 calm이고 counters는 ...`

### 캐릭터 말풍선 (tteoki가 말하는 톤)
- 짧음 (8자 이내 권장, 최대 15자)
- 친근·반말 가능 (한국 사용자 기준)
- 이모지 1개 이내 (과다 X)

✅ "오늘도 잘해보자"
✅ "배터리 좀 챙겨주세요"
✅ "헐… 일 많네"
✅ "고마워!"

❌ "안녕하세요. 저는 tteoki입니다. 오늘 하루도 화이팅!"  (너무 김)
❌ "배터리 충전 권장 🔋⚡💪"  (이모지 과다)

### 웹사이트·README 톤 (작가 톤)
- 영문: 간결·드라이·약간 유머
- 한글: 평어체·짧은 문장
- 마케팅 과장 X — "수집·자랑·재미" 사실만 짚기

✅ "Claude Code 옆에 작은 친구가 있다면."
✅ "키캡 옆에 둘 친구, tteoki."

❌ "혁신적인 AI 어시스턴트 마스코트!"
❌ "당신의 코딩을 새로운 차원으로!"

---

## 로고·아이콘

### 로고 (chibi-mcp 워드마크)
```
   ⊂(◍•ᴥ•◍)⊃   chibi-mcp
   ───────
   캐릭터 + 워드마크 가로 조합
```
- 캐릭터 아이콘 + 워드마크 두 형태 모두 사용
- 단독 캐릭터 아이콘만 사용 가능 (favicon·SNS profile)
- 색상: Light/Dark 두 버전 SVG

### Favicon
- 32×32 tteoki 얼굴 (단순화)
- ICO + PNG + SVG 모두 제공

---

## UI 컴포넌트

### 데스크탑 앱 (Tauri)

#### Pet Window (펫 모드)
- transparent background
- always-on-top (사용자 토글 가능)
- 크기: 220~260px
- 위치: 화면 우하단 (사용자 드래그로 이동 가능)
- 닫기 버튼: 우클릭 → 메뉴
- 정보 밀도: 닉네임/희귀도, 한국어 기분명, `N/간격 · 도막 · 티켓`까지만
- 캐릭터 아래 낮은 타원 그림자. 장식용 큰 패널/카드는 쓰지 않음
- slice 이벤트: flash + 작은 도막 낙하. 설명 텍스트는 띄우지 않음
- 옵션 레이어: 최대 3개까지 본체 위에 합성. 시럽/연유/소스는 상단 드립, 가루/씨앗/팥/꽃잎/레진은 표면 장식으로 유지한다.

#### Notification Window (알림 모드)
- 화면 우상단 슬라이드 인
- 크기: 280×80px (캐릭터 60×60 + 텍스트)
- 자동 사라짐: 3초 후 fade out
- 클릭 시: 유지 (사용자가 직접 닫을 때까지)

#### Widget Window (위젯 모드)
- 화면 좌상단 도킹 (기본)
- 크기: 260×180px
- 내용: CPU/RAM/BAT 그래프 + 캐릭터 옆에
- 배경: glassmorphism (반투명 + blur)

#### Settings Window
- 크기: 480×640px
- 탭: 모드 / 캐릭터 / 사운드 / Claude 연동 / 정보
- 모던 minimal — chibi 느낌 약간만 (브랜드 일관성)

### 웹사이트 (chibi-mcp.dev)

#### 색상 — Brand
```
Primary:   #FFE5EC  (tteoki 핑크)
Secondary: #2C2C2C  (텍스트·outline)
Background: #FFFFFF (white)
Accent:    #FF6B9D  (CTA 버튼)
```

#### 레이아웃
```
┌──────────────────────────────────────────┐
│  [chibi-mcp]              [GitHub] [DL]   │
├──────────────────────────────────────────┤
│                                            │
│       ⊂(◍•ᴥ•◍)⊃                            │
│        tteoki                            │
│                                            │
│   "Claude Code 옆에 작은 친구가 있다면."    │
│                                            │
│         [Download for macOS]               │
│         [Download for Windows]             │
│         [Download for Linux]               │
│                                            │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                            │
│         [데모 GIF/Video]                   │
│                                            │
├──────────────────────────────────────────┤
│  Setup in 30s                              │
│                                            │
│  $ claude mcp add chibi -- npx chibi-mcp   │
│                                            │
│  And run the desktop app.                  │
└──────────────────────────────────────────┘
```

### GitHub README 구조

```markdown
# chibi-mcp

> Your tiny friend for Claude Code.

[데모 GIF — 12초, tteoki가 출렁이며 CPU 변화에 반응]

## Quick start (30 seconds)

\```bash
claude mcp add chibi -- npx chibi-mcp
\```

Then download the desktop app: [Releases](#)

## Features

- 🍡 chibi 캐릭터가 화면 옆에 항상
- 🎵 슬라임 ASMR 사운드 (선택)
- ⚡ CPU/RAM/배터리 표정으로 표시
- 🔌 Claude Code · Codex MCP 호환
- 🆓 100% 무료 · 코드 MIT · 에셋 권리 문서화

## 4 Modes (all free)

| 펫 | 알림 | 위젯 | VTuber |
[각 모드 스크린샷]

## How it works

[아키텍처 다이어그램]

## Sounds & Motions

[슬라임 ASMR 영감 — 출처 표기]

## Roadmap

- [x] v0.1 Pet mode + sound
- [ ] v0.2 Notification mode
- [ ] v0.3 Widget mode + (maybe) seasonal characters
- [ ] v0.4 Live2D

## Credits

캐릭터 디자인: ...
사운드: CC0 sources from Freesound.org

## License

Code: MIT
Assets and pack submissions: see ASSET_RIGHTS.md
```

---

## SNS 공유 카드 디자인

### 인스타그램 정사각형 (1080×1080)
```
┌────────────────────────────────────────┐
│  배경: 그라데이션 #FFE5EC → #FCE38A     │
│                                          │
│           ⊂(◍•ᴥ•◍)⊃                      │
│           (tteoki 그림 큼)             │
│                                          │
│         "오늘도 같이 코딩!"             │
│         ── tteoki #047                │
│                                          │
│  ⏱️ 3h 22m   ⌨️ 47 calls   🍡 1/?       │
│                                          │
│                                          │
│                    chibi-mcp.dev         │
└────────────────────────────────────────┘
```

### 트위터 가로 (1200×675)
- 같은 정보, 가로 비율
- 우측에 캐릭터, 좌측에 텍스트

### 인스타그램 스토리 (1080×1920)
- 세로 비율
- 상단 캐릭터, 중단 메시지, 하단 정보

---

## 사운드 사용 가이드

### 사용자 첫 실행 시 — 사운드 동의
```
┌────────────────────────────────────┐
│   🎵 tteoki가 슬라임 사운드를     │
│      들려줘도 될까요?              │
│                                      │
│   (ASMR 느낌, 매우 작은 음량)       │
│                                      │
│   [네 좋아요]  [지금은 아니요]      │
│                                      │
│   언제든 설정에서 변경 가능         │
└────────────────────────────────────┘
```

### 기본 볼륨
- 시작: 30% (사용자가 조절)
- 무음 모드: 시스템 음소거 자동 감지
- 야간 모드: 22시~07시 자동 -50%

---

## 글로벌 vs 로컬 톤

### 영문 (글로벌 GitHub·ProductHunt·HackerNews)
- 톤: 간결·드라이·약간 self-aware
- 마케팅 헤드라인: "Your tiny friend for Claude Code."
- ASMR을 글로벌 어필 포인트로

### 한글 (한국 디시·트위터·인스타그램)
- 톤: 친근·반말 가능·인디 감성
- 마케팅 헤드라인: "Claude Code 옆에 작은 친구를."
- 키캡·슬라임 트렌드를 한국 어필 포인트로

---

## 검토 체크리스트

- [ ] 5가지 디자인 원칙에 동의?
- [ ] 타이포그래피 (Inter + Pretendard + Quicksand) 좋은가?
- [ ] 캐릭터 보이스 톤 (짧은 반말) 좋은가?
- [ ] 웹사이트 레이아웃 hero 영역 좋은가?
- [ ] GitHub README 구조 충분한가?
- [ ] SNS 공유 카드 정보 (시간·호출수·컬렉션) 좋은가?
- [ ] 사운드 동의 UX (첫 실행 시 묻기) 좋은가?
