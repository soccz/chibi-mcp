---
name: chibi-surface-sync
description: chibi-mcp의 다중 표면에 복제된 정보(버전·도구목록·카탈로그·가챠로직·문구풀·WS상수)를 어디서 어떻게 동기화하는지의 드리프트 맵. chibi-surface-sync 에이전트가 코어 변경 후 표면 전파 시 사용. 버전 범프, 새 도구, 새 캐릭터/옵션, 가챠 변경, 문구 변경, WS 상수 변경 시 반드시 적용.
---

# chibi-surface-sync — 드리프트 맵

chibi-mcp의 같은 정보는 여러 표면에 복제되어 있다. 정본 런타임은 Python 패키지, 나머지는 그것을 등록/호출하거나 일부를 재구현한다. 어떤 변경이든 **아래 6개 드리프트 항목을 전부 훑고**, 각각 [전파함 / 해당없음 / 패리티갭 보류]로 보고한다.

## 드리프트 항목 1 — 버전 문자열 (3개 독립 라인)

**`1.4.39` 라인** (Python+플러그인, 한 덩어리로 움직임):
- `server/chibi_mcp/__init__.py` (`__version__`) ← 정본
- `server/pyproject.toml`
- `.claude-plugin/plugin.json`
- `.codex-plugin/plugin.json`
- 산문 참조(검사 대상): `INSTALL.md`, `README.md`, `server/tests/test_cli.py`(`EXPECTED_VERSION`), 인스톨러 스크립트(`EXPECTED_VERSION`)
- `verify_all.sh` 3단계가 `__version__ == pyproject == 두 plugin.json` 일치를 강제. 4개 중 하나라도 어긋나면 게이트 실패.

**`0.5.3` 라인** (VS Code, **별도 cadence — 함께 올리지 않는다**):
- `vscode-ext/package.json`만. (확장 id `soccz.chibi-mcp`.)

**`0.2.0-alpha.1` 라인** (Rust, 별도):
- `server-rs/Cargo.toml` + `server-rs/src/main.rs`의 시작 로그 문자열 리터럴.

## 드리프트 항목 2 — MCP 도구 목록 (4곳)

정본 레지스트리: `__main__.py`의 `_TOOL_FUNCTIONS`(16개) + `server.py`의 `@mcp.tool()`. 도구 추가/이름변경 시:
- `skills/chibi/SKILL.md` — frontmatter description이 도구 이름을 **열거**한다(현재 16개 전부가 아니라 사용자 노출용 11개 subset만 열거). 새 도구가 사용자 직접 호출 대상이면 갱신.
- `commands/chibi.md` — 한국어 키워드→도구 라우팅 매핑(현재 9개 라우팅). 새 도구의 트리거 추가.
- `server-rs/src/main.rs` — 16개 중 **4개만** 구현(`get_pet_state, pet_say, slice_now, set_slice_interval`). 나머지(gacha/inventory/window/catalog)는 패리티 갭. 새 도구를 Rust에 꼭 포팅할 필요는 없지만, 포팅 안 하면 **보고서에 패리티 갭으로 명시**.

## 드리프트 항목 3 — 카탈로그 / 에셋 meta.json

**byte-identical 3중 사본** (하나 고치면 셋 다 동일하게 — `diff`/`md5sum`으로 확인):
- `assets/meta.json` ← 런타임 정본
- `server/chibi_mcp/assets/meta.json` (휠에 패키징)
- `vscode-ext/resources/meta.json`

주의: `test_option_assets.py`는 byte-identity를 **강제하지 않는다**. 자유 옵션 id 순서 + 권리 top-level 필드 + 이미지 512×512 RGBA 규격만 대조하므로, `name_ko`/`category`/`description`이나 characters 배열만 한쪽에서 바뀌면 테스트는 통과한다. 세 사본의 완전 일치는 테스트가 아니라 직접 diff로 확인하라.

스키마: `tier: free | upcoming`(`upcoming`은 `locked:true` 숨김). 8 free 캐릭터 + 12 free 옵션 레이어. 권리 필드(`no_third_party_ip`, `permission_scope` 등) 포함 — `verify_all.sh` 15섹션(권리 정책)이 검사.

**발산하는 설계 마스터** (별개, 맹목 복사 금지):
- `characters/characters_meta.json` — 29종, `tier: free | pro`(`pro`≠`upcoming`!), 실제 한글명("흰떡","백설기","모찌"...), `options` 없음. CHARACTER_DESIGN.md와 일치하는 설계 목록. 같은 id가 양쪽에 있지만 `name_ko`/`category`/`tier`가 다름.
- `desktop/src/characters/meta.json` — 레거시 Tauri용 또 다른 사본(archival, 보통 안 건드림).

> 새 캐릭터/옵션을 런타임에 노출 → 3중 사본 동일 갱신 + 권리 필드 채움. 설계 목록에만 추가 → `characters_meta.json`.

## 드리프트 항목 4 — 가챠 로직 (3곳)

- `server/chibi_mcp/state.py` + `server.py`(`pull_gacha`) ← 정본 로직.
- `vscode-ext/src/extension.ts` — **자체 재구현**. `RARITY_WEIGHTS = {5:1,4:5,3:24,2:70}` 복제 + 일일 출석 티켓. webview 가챠는 MCP를 안 부르고 `context.globalState`에 자체 인벤토리.
- `skills/chibi/SKILL.md` — 가챠 규칙을 산문으로 문서화(무료 일일 풀, 100콜/+1, 10마일스톤/+1).

> 가중치/티켓 규칙 변경 시 3곳 모두.

## 드리프트 항목 5 — 문구 풀 / say 브리지 (2곳)

- `bin/chibi-react.sh` — Claude 훅. 도구별 한국어 문구, ~30% 샘플. `chibi-say`(pre) / `chibi-say --tool-call`(post) 호출.
- `vscode-ext/src/extension.ts` — `chibiSay()`, ~40% 샘플 + 6초 쿨다운. save/task/debug 이벤트에서 `spawn("chibi-say",...)`. 자체 문구 풀.

> 둘 다 결국 `chibi-say` CLI를 부른다. 문구/샘플링을 손보면 양쪽 인지.

## 드리프트 항목 6 — WS 프로토콜 상수

`ws://127.0.0.1:9876`:
- Python: `ws_server.py`(`DEFAULT_WS_HOST/PORT`), `__main__.py`, `cli.py`, `server.py`(`_window_ws_url`)
- Rust: `server-rs/src/ws_server.rs`(`DEFAULT_HOST`/`DEFAULT_PORT`)
- 메시지 타입(state/say/slice/sound)도 양쪽 일치 필요. 공유 프론트엔드(Tk/Tauri)가 의존.

## 산문 카운트 (드리프트 주의)
- `skills/chibi/SKILL.md`: "8 starter characters"
- `vscode-ext`: 소유 카운트 UI "/ 29"
- 카탈로그가 바뀌면 이 숫자도 어긋난다 — docs-keeper와 분담 확인.

## 산출물 형식

`_workspace/03_sync_report.md`:
```markdown
# Surface Sync Report
1. 버전: [전파함: 어느 파일 / 해당없음]
2. 도구 목록: [전파함 / 해당없음 / Rust 패리티갭: <도구명>]
3. 카탈로그 meta.json: [3중 사본 동일 갱신함 / 해당없음]
4. 가챠 로직: [전파함 / 해당없음]
5. 문구 풀: [전파함 / 해당없음]
6. WS 상수: [전파함 / 해당없음]
산문 카운트: [갱신함 / 해당없음]
기존 드리프트 발견: <있으면 어느 쪽이 정본인지 근거와 병기>
```

## 원칙
- byte-identical은 byte-identical로. 기존에 어긋난 드리프트는 임의로 한쪽 삭제하지 말고 정본 판단 근거와 함께 병기.
- core-dev가 통보한 변경에 반응하는 역할. 코어 로직을 직접 재설계하지 않는다.
