---
name: chibi-dev
description: chibi-mcp 개발 작업의 오케스트레이터. 기능 추가·버그 수정·리팩터·표면 동기화·문서 갱신·배포 준비를 guardian→(core-dev/surface-sync/docs-keeper)→verifier 에이전트 팀으로 조율한다. "chibi 서버/창/도구/가챠 기능 추가/수정", "버그 고쳐", "버전 올려", "캐릭터/옵션 추가", "표면 동기화", "다시 실행/재실행/업데이트/보완", "이전 결과 기반으로 개선", "배포 준비" 등 chibi-mcp 코드·문서·배포 작업 요청 시 사용. 단순 질문(코드 위치·동작 설명)은 직접 응답 가능. (런타임 펫 제어 — 펫 띄워줘/뽑기 — 는 shipped 'chibi' 스킬 소관이지 이 스킬 아님.)
---

# chibi-dev — chibi-mcp 개발 오케스트레이터

chibi-mcp의 코드·문서·배포 변경을 5인 에이전트 팀으로 조율한다. 이 레포의 두 핵심 특성 — **다중 표면 중복**과 **엄격한 결정 영역 가드레일** — 때문에 변경 하나가 여러 표면·문서로 번지고, 사용자 결정 영역을 임의로 건드리면 안 된다. 그래서 guardian이 앞에서 막고, 구현 3인이 코어/표면/문서를 나눠 맡고, verifier가 게이트한다.

**실행 모드: 에이전트 팀.** core-dev의 변경에 surface-sync가 의존하고 verifier가 둘 다 검증하므로, 실시간 조율(SendMessage)과 공유 작업 목록(TaskCreate)이 품질을 높인다. 모든 Agent/팀원 호출은 `model: "opus"`.

팀원 (정의: `.claude/agents/`):
- **chibi-guardian** — 가드레일·범위 게이트 (스킬: chibi-guardrails)
- **chibi-core-dev** — Python 서버·창 구현 (스킬: chibi-server-dev)
- **chibi-surface-sync** — 중복 표면 전파 (스킬: chibi-surface-sync)
- **chibi-docs-keeper** — 문서·SPEC (스킬: chibi-docs)
- **chibi-verifier** — 검증 게이트 (스킬: chibi-verify) · **`subagent_type: "general-purpose"`로 스폰** (verify_all.sh/pytest를 실제 실행해야 하므로 읽기 전용 Explore/Plan 금지)

---

## Phase 0: 컨텍스트 확인

작업 디렉토리 하위 `_workspace/` 존재 여부로 실행 모드를 정한다:
- `_workspace/` **미존재** → **초기 실행** (전체 워크플로우)
- `_workspace/` **존재 + 사용자가 부분 수정 요청**("X만 다시", "이 부분 보완") → **부분 재실행** (해당 에이전트만 재호출, 이전 산출물 읽고 개선)
- `_workspace/` **존재 + 새 입력/새 기능** → **새 실행** (기존 `_workspace/`를 `_workspace_prev/`로 이동 후 초기 실행)

`_workspace/`는 작업 디렉토리(레포 루트) 하위에 만든다. 파일 컨벤션: `01_guardian_scope.md`, `02_coredev_changes.md`, `03_sync_report.md`, `04_docs_report.md`, `05_verify_report.md`.

---

## Phase 1: 가드레일·범위 게이트 (guardian)

먼저 **chibi-guardian** 하나만 호출한다(`model: "opus"`). guardian은 chibi-guardrails 스킬로 요청을 분류하고 `_workspace/01_guardian_scope.md`를 쓴다.

- **차단 사항이 있으면**(사용자 결정 영역에 걸림) → **여기서 멈추고 사용자에게 해당 결정 항목을 질문한다.** 팀을 만들지 않는다. 추측 진행 금지.
- 차단 사항이 없으면 → scope의 작업 범위(core-dev/surface-sync/docs-keeper 중 누가 필요한지)를 읽고 Phase 2로.

> guardian은 읽기·분석 + scope 파일 쓰기만 한다. 코드/문서를 편집하지 않는다.

---

## Phase 2: 구현 (팀)

scope가 지정한 **필요한 에이전트만**으로 팀을 구성한다. 모든 변경에 3인이 다 필요한 건 아니다:
- 순수 코드 버그 → core-dev (+ 영향 시 surface-sync) + verifier
- 버전 범프/카탈로그 추가 → surface-sync + docs-keeper + verifier
- 도구 추가 → core-dev → surface-sync → docs-keeper + verifier (풀 파이프라인)

`TeamCreate`로 팀을 만들고 `TaskCreate`로 의존 관계를 가진 작업을 할당한다. 데이터 흐름:

```
guardian scope
   │
   ├─ core-dev ───(복제값/도구 변경 통보)──▶ surface-sync
   │      │                                      │
   │      └──────────────┬───────────────────────┤
   │                     ▼                        ▼
   │                docs-keeper ◀──(변경 요약)── (둘 다)
   │                     │
   └─────────────────────┴──────▶ verifier (점진적 + 최종)
```

- **의존 순서가 중요하다.** surface-sync는 core-dev가 "무엇을 바꿨는지" 알아야 전파한다. core-dev가 먼저 끝내고 SendMessage로 변경값을 통보 → surface-sync 착수. docs-keeper는 둘의 변경 요약을 받아 문서화.
- 독립적인 부분(예: 코드와 무관한 문서 갱신)은 병렬 가능.
- **verifier는 점진적으로 호출한다.** core-dev가 끝나면 즉시 코어 검증, surface-sync가 끝나면 일관성 검증, 전부 끝나면 `make check` 최종 게이트. (chibi-verify 스킬의 점진적 QA 표 참조.)

각 팀원은 자기 스킬을 읽고 `_workspace/0N_*.md`에 산출물 요약을 남긴다.

---

## Phase 3: 최종 게이트 · 종합

verifier의 최종 `make check`(또는 환경상 가능한 범위) 결과를 받는다.
- **통과** → 변경 요약(건드린 파일, 표면, 문서, 검증 결과)을 사용자에게 보고.
- **실패** → verifier가 책임 에이전트에 회부한 항목을 1회 재수정 사이클 돌린다(아래 에러 핸들링). 그래도 실패면 누락을 명시해 보고.

---

## 데이터 전달 프로토콜

- **태스크 기반**(`TaskCreate`/`TaskUpdate`): 진행상황·의존 관계.
- **파일 기반**(`_workspace/`): 각 단계 산출물 요약. 사후 감사·재실행용으로 보존. 최종 코드/문서 변경은 레포 본체에.
- **메시지 기반**(`SendMessage`): core-dev→surface-sync 변경 통보, verifier→책임에이전트 실패 회부 등 실시간 조율.

---

## 에러 핸들링

- **1회 재시도 원칙.** 에이전트 작업 실패 시 1회 재호출. 재실패면 그 결과 없이 진행하고 보고서에 누락 명시.
- **검증 실패 회부.** verifier가 실패를 발견하면 직접 안 고치고 책임 에이전트(코드→core-dev, 표면→surface-sync, 문서→docs-keeper)에 구체적 출력과 함께 회부. 1회 수정 사이클 후 재검증.
- **환경 부재 ≠ 코드 실패.** cargo/claude/codex/pwsh/디스플레이 부재로 skip된 단계는 실패가 아니라 skip으로 보고. verify_all.sh는 cargo 부재를 하드 실패로 보므로, Rust 미설치 환경에서는 `make server-test`+`--check`+표면 일관성으로 대체 검증하고 그 사실을 명시.
- **상충 데이터는 삭제하지 않고 병기.** 기존 표면 드리프트가 발견되면 어느 쪽이 정본인지 근거와 함께 둘 다 보고.
- **사용자 결정 충돌은 항상 사용자에게.** guardian이 못 잡았더라도 구현 중 사용자 결정 영역이 드러나면 멈추고 회부.

---

## Phase 7: 실행 후 진화

작업 완료 후 사용자에게 한 번 기회를 준다: "결과나 팀 구성/워크플로우에서 바꾸고 싶은 점이 있나요?" 피드백이 오면 유형별로 반영하고 `CLAUDE.md`의 하네스 변경 이력에 기록한다:
- 결과 품질 → 해당 스킬 수정 / 에이전트 역할 → 에이전트 `.md` / 워크플로우 순서 → 이 오케스트레이터 / 트리거 누락 → description 확장.

---

## 테스트 시나리오

### 정상 흐름 — 새 MCP 도구 `set_view_mode` 추가
1. Phase 0: `_workspace/` 없음 → 초기 실행.
2. guardian: "도구 추가는 코드·문서 일반, 위임설계도 사용자결정도 아님. 가드레일 통과(무료·크로스플랫폼 OK)." 차단 없음. scope: core-dev(server.py+__main__.py), surface-sync(SKILL.md/commands/server-rs 패리티갭), docs-keeper(있으면 README).
3. core-dev: `server.py`에 `@mcp.tool()` + `__main__.py` `_TOOL_FUNCTIONS` 추가, 테스트 추가, 국소 pytest 통과 → surface-sync에 "도구 set_view_mode 추가" 통보.
4. surface-sync: `skills/chibi/SKILL.md` description·`commands/chibi.md` 라우팅 갱신, server-rs는 패리티갭으로 보고.
5. verifier: 도구 등록 교차 비교(코어 16→17, SKILL 일치) + `make check`. 통과 → 보고.

### 에러 흐름 — 버전 범프 시 표면 하나 누락
1. surface-sync가 `__init__.py`만 1.4.40으로 올리고 plugin.json 둘을 빠뜨림.
2. verifier: verify_all.sh 3단계 "버전 불일치" 실패 출력 캡처 → surface-sync에 회부.
3. surface-sync: pyproject + 두 plugin.json 정렬(0.5.3 vscode·0.2.0 rust는 건드리지 않음).
4. verifier 재검증 통과 → 보고.

### 차단 흐름 — 사용자 결정 영역
1. 요청: "팀 에디션 유료 기능 넣자."
2. guardian: 수익화 모델·상업 트랙은 사용자 결정 영역 + 가드레일 1·2 위반(무료 유지). 차단 사항 기록.
3. 오케스트레이터: 팀 만들지 않고 사용자에게 "팀 에디션 유료화는 사용자 결정 영역이며 현재 무료 정책과 충돌합니다. 진행할까요?" 질문.
