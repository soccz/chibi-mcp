# chibi-mcp — SPEC

> 작성일: 2026-05-18
> 본 문서는 사용자가 직접 또는 함께 결정한 사항만 기록한다.

---

## 사용자가 명시한 요구사항

1. **MCP 서버로 등록 가능한 형태** (Claude Code / Codex MCP)
2. **GitHub에서 설치하는 형식** — Claude Code/Codex 사용 시 한 줄로 설치
3. **노트북·화면에서 CPU·배터리 등 시스템 정보 표시**
4. **캐릭터성**을 가진 캐릭터 (단순 알림이 아닌 성격 있는 마스코트)
5. **한국 인기 트렌드 (아티잔 키캡 + 슬라임 ASMR) 반영** — 출처 명확
6. **새로우면서 익숙한** 디자인 — 틱톡·유튜브 조회수 높은 사운드/모션/스타일 반영
7. **디자인은 위임됨** — 모션·사운드·스타일·색감은 출처 조합해 결정
8. **떡 종류 시리즈** (사용자 제안 2026-05-18) — 디자인하기 좋은 떡 다 포함
9. **가래떡 베이스 + 조청 흐르는 모션** (사용자 제안 2026-05-18)
10. **시간 흐름 시각화** (사용자 제안 2026-05-18) — 가래떡 길어지는 모션 + 자르는 모션 활용
11. **상업적으로 더 다양하게 강화** (사용자 요청 2026-05-29) — 무료 코어를 유지하면서 캐릭터 콘텐츠, 팀 배포, 크리에이터 팩, 브랜드 콜라보, 물리 굿즈 등으로 확장 가능한 구조 검토
12. **요즘 출처 기반으로 GitHub star 받을만한 형태 강화** (사용자 요청 2026-05-29) — AI coding/MCP 흐름, GitHub community 표준, social preview, topics, showcase loop 반영
13. **상업화 기반 기능까지 진행** (사용자 요청 2026-05-29) — 데모/공유, 정식 배포 준비, 캐릭터팩 SDK, 신뢰 리포트, 팀 에디션 준비를 무료 코어 위에 추가
14. **옵션 이미지 계열 추가** (사용자 요청 2026-05-29) — 꿀, 조청, 비즈/스프링클에서 시작해 연유, 콩가루, 흑임자, 팥, 꽃잎, 레진 별, 말차, 매콤 소스까지 무료 시각 옵션 레이어를 캐릭터 위에 합성 가능하게 추가

---

## 같이 결정한 사항

| 항목 | 결정 |
|---|---|
| 프로젝트명 | **chibi-mcp** |
| 플랫폼 | **크로스플랫폼 (Tauri/Electron)** |
| 4가지 모드 | **다 넣기** — 모드 선택으로 사용자가 전환 |
| 4모드 종류 | 데스크탑 펫 / 알림형 / 위젯형 / VTuber 풍 |
| 라이센스 | **100% 무료** (본체) |
| 수익화 시점 | **트래픽 쌓이면 결정** (지금은 결정 보류) |
| 가챠/뽑기 검토 | 향후 검토. 모델은 추후 결정 |
| 모션·사운드 투자 수준 | **할 수 있는데까지** |

---

## Step A 결정사항 (2026-05-18)

| 항목 | 결정 |
|---|---|
| **MVP 범위** | 4모드 공통 코어 먼저 + 펫 모드만 클라이언트 |
| **일정 압박** | 자유 페이스 (마감일 없음) |
| **출시 채널** | GitHub Public Release (현재). 트래픽 보고 ProductHunt·HN·한국 커뮤니티 추가 검토 |
| **캐릭터 이름** | **tteoki (떡이)** — 한국 떡 + 귀여움 어미 '이'. 사용자 결정 2026-05-18 |
| **캐릭터 모양 컨셉** | **한국 떡 종류 시리즈** (사용자 제안). 디자인하기 좋은 떡 풀 다 포함 |
| **베이스 캐릭터** | **가래떡 + 조청 흐르는 모션** (사용자 선택 2026-05-18). 가로로 길쭉한 형태 + 표면 조청 drip 애니메이션 |
| **자르기 트리거** | **Claude 호출 N회마다 자동** (디폴트 10회, 사용자 설정 가능). 자른 도막은 화면 하단 누적 후 fade out |
| **상업 확장 원칙** | **무료 코어 유지 + 콘텐츠/팀/콜라보/굿즈 확장 후보 검토**. 네 가지 모드와 MCP 기본 기능은 유료 게이트로 막지 않음 |
| **상업화 기반 CLI** | `chibi-audit`, `chibi-pack init/validate/preview`, `chibi-share` 추가. 결제/유료 게이트가 아니라 신뢰·콘텐츠·공유 루프 기반 |
| **무료 옵션 레이어** | 12종 추가: `jocheong_drip`, `honey_glaze`, `sugar_beads`, `rainbow_sprinkles`, `condensed_milk`, `kinako_dust`, `black_sesame`, `red_bean_bits`, `flower_petals`, `resin_stars`, `matcha_powder`, `spicy_sauce`. 본체 기능을 잠그지 않는 무료 코스메틱 기반 |

## 아직 사용자 결정 대기

| 항목 | 상태 |
|---|---|
| 추가 떡 종류 출시 순서 | 진행 중 (후보 검토) |
| 성공 지표·트래픽 기준 | `[미정 — 출시 후 결정]` |
| 가챠/Drop 모델 | `[미정 — 트래픽 누적 후 결정]` |
| 추가 출시 채널 시점 | `[미정 — 트래픽 본 뒤]` |
| 직접 구매 캐릭터팩 | `[미정 — 상업화 단계에서 결정]` |
| 크리에이터 마켓플레이스 | `[미정 — pack schema/검수 기준 먼저 필요]` |
| 팀/조직용 유료 지원 | `[미정 — 팀 설치 수요 확인 후 결정]` |
| 브랜드 콜라보·물리 굿즈 | `[미정 — 파트너/수요 확인 후 결정]` |
| GitHub topics 실제 설정 | `[GitHub repo settings에서 수동 설정 필요]` |
| social preview 이미지 업로드 | `assets/social-preview.png` 생성됨. GitHub repo settings 업로드는 수동 필요 |

---

## 위임받은 영역 (사용자가 "디자인은 너가" 명시)

- 캐릭터 비율·표정·모션 시스템
- 사운드 라이브러리 (슬라임 ASMR 출처 매핑)
- 색상 팔레트
- 타이포그래피
- UI 컴포넌트 시각 톤
- 출처 조합 방식

자세한 내용: [CHARACTER_DESIGN.md](CHARACTER_DESIGN.md), [STYLE_GUIDE.md](STYLE_GUIDE.md).

상업 확장 후보와 유료화 가드레일: [COMMERCIAL_STRATEGY.md](COMMERCIAL_STRATEGY.md).

GitHub star 성장 전략: [GITHUB_STAR_STRATEGY.md](GITHUB_STAR_STRATEGY.md).

---

## 출처 (사용자 요구사항: "출처 명확하게")

### 아티잔 키캡
- [Artisan Keycap History](https://artisancollector.com/artisan-keycap-history/) — 한국 메이커 GirlDC 2012년 metal artisan keycap 시초
- [SMKX 2026 — Seoul Mechanical Keyboard Expo](https://www.klc-smkx.com/) — 78개 글로벌 키보드·키캡·아티잔 브랜드 참가
- [Aihey Studio](https://aiheystudio.com/collections/artisan-keycaps), [3ditda 쪼꼬미 키캡](https://www.3ditda.com/product/artisan_littlecat-100), [S-craft.studio](https://rebyte.kr/112)

### 슬라임 ASMR
- [TikTok #slimeasmr](https://www.tiktok.com/tag/slimeasmr) — TikTok 4.8억 게시물
- [The Asian — 슬라임이 뭐죠?](http://kor.theasian.asia/archives/184133) — 한국 슬라임 6만+ 영상, 조회수 2000만+
- [Audicus — Crunchy Slime ASMR](https://www.audicus.com/blog/entertainment/crunchy-slime-asmr/) — ASMR 2024 YouTube 최다 검색어, 연 650억 뷰
- [ReelMind — Sensory Content Trends](https://reelmind.ai/blog/trending-youtube-videos-slime-asmr-and-sensory-content-trends) — 2025 sensory video 시장 $1.5B

### chibi 디자인
- [Chibi.pics — What is Chibi & Why Popular](https://www.chibi.pics/blog/what-is-chibi-why-its-style-is-so-popular)
- [Scipuz — Viral Chibi Cartoon AI Trend](https://scipuz.com/viral-chibi-cartoon-ai-photo-prompt-for-girl-trend/) — Gemini·ChatGPT chibi 변환 트렌드

### 한국 2025 마스코트 트렌드
- [캐릿 — 라이징 캐릭터 20](https://www.careet.net/1853) — 쿠이·쥬니햄·히히클럽
- [캐릿 — 2025 트렌드 키워드](https://www.careet.net/Content/CurationList?Id=2) — "머릿속 텅 빈 표정" 트렌드
- [고구마팜 — 2025 사랑받은 캐릭터](https://gogumafarm.kr/)

### 기존 데스크탑 펫 (참고·차별점 확보용)
- [Kilkakon Shimeji-ee](https://kilkakon.com/shimeji/), [shimejis.xyz](https://shimejis.xyz/) — 2010년대 픽셀 스타일. chibi-mcp는 SVG 벡터 + ASMR 사운드로 차별
