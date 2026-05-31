---
name: chibi-server-dev
description: chibi-mcp Python 서버 코어와 Tk 펫 창을 구현하는 방법 — MCP 도구 이중 등록(server.py + __main__.py), 무드·가챠·상태 모델, localhost WebSocket 프로토콜, detached 창 subprocess, 크로스플랫폼 사운드/창 분기, 어떤 기능이 어느 파일에 사는지. chibi-core-dev가 server/chibi_mcp/* 를 편집할 때 사용. MCP 도구 추가/수정, 무드/가챠 변경, WS 변경, 창 렌더링/모션/사운드 작업 시 반드시 적용.
---

# chibi-server-dev — Python 서버·창 구현 가이드

정본 런타임은 `server/chibi_mcp/` 패키지다. 어디를 건드릴지부터 정한다.

## 어느 파일을 건드리나 (기능 → 파일)

| 하려는 일 | 파일 |
|----------|------|
| MCP 도구 추가/수정 | `server.py` (`@mcp.tool()`) **+** `__main__.py` (`_TOOL_FUNCTIONS`) — 둘 다! |
| 무드 임계값·가챠·인벤토리·티켓·영속화 | `state.py` |
| WebSocket 메시지 타입/브로드캐스트 | `ws_server.py` |
| CPU·RAM·배터리 읽기 | `system_info.py` |
| 런타임 디렉토리/파일 경로 | `runtime.py` |
| 무료 정책/카탈로그 티어 필터 | `license.py` |
| 펫 창 렌더링·모션·사운드·UI | `window.py` (독립 프로세스, 3,900줄) |
| chibi-audit/pack/share CLI | `commercial.py` |
| chibi-say/chibi-check CLI | `cli.py` |
| MCP 핸드셰이크/stdio/--check/--doctor/--open/--ws-only | `__main__.py` |

## ⚠️ 도구 이중 등록 (가장 흔한 함정)

FastMCP의 stdio 전송은 **의도적으로 우회**되어 있다(FastMCP stdio 출력이 Claude Code 헬스체크를 깨서). 실제로 도는 건 `__main__.py`의 손수 짠 JSON-RPC이고, `tools/list`·`tools/call`은 `_TOOL_FUNCTIONS` dict를 순회한다. 스키마는 함수 시그니처+docstring에서 합성된다.

**도구를 추가/이름변경하면 두 곳을 고친다:**
1. `server.py` — `@mcp.tool()` 데코레이터 + 함수 본문 + **명확한 docstring과 타입 힌트**(스키마 합성에 쓰임)
2. `__main__.py` — `_TOOL_FUNCTIONS` dict에 `"tool_name": server_tools.tool_name` 추가

`_TOOL_FUNCTIONS`에 없으면 Claude/Codex에 도구가 안 보인다. 현재 16개 도구:
`get_pet_state, pet_say, slice_now, get_license_status, get_catalog, get_options, set_active_options, clear_active_options, open_pet_window, close_pet_window, set_slice_interval, pull_gacha, get_inventory, set_active_character, rename_character, add_ticket`

> 도구 목록을 바꾸면 표면(SKILL.md/commands/server-rs)에도 복제되어 있다 → surface-sync에 통보.

## 상태 모델 (`state.py`)

- `ChibiState` 데이터클래스 + `Lock`. `get_state()` 싱글톤(이중검사 락). 테스트는 `reset_state_for_tests()`.
- 영속화: `~/.chibi-mcp/state.json`, schema **v4**, tmp 파일 + 원자적 `replace`. **영속되는 것**: inventory, tickets, active_character_id, active_option_ids, slice_interval. 카운터는 서버 수명마다 리셋.
- 무드 `Mood` StrEnum: `calm / panting / drowsy / lonely / happy / surprised / joyful`. `compute_mood()`가 CPU/배터리/유휴에서 도출. 임계값 변경 시 `test_state.py`와 server-rs(`state.rs`, 패리티) 양쪽 영향.
- 가챠: `RARITY_WEIGHTS = {5:1, 4:5, 3:24, 2:70}`. 첫 일일 풀 무료, 이후 1티켓. 티켓 적립: 100콜마다 +1, 슬라이스 10회마다 +1. `MAX_ACTIVE_OPTIONS = 3`. (이 규칙은 vscode-ext와 SKILL 문서에도 복제 → surface-sync.)
- `snapshot()`이 WS가 브로드캐스트하고 도구가 반환하는 전체 dict.

## WebSocket 프로토콜 (`ws_server.py`)

- `ws://127.0.0.1:9876` (env `CHIBI_WS_HOST`/`CHIBI_WS_PORT`). `websockets>=14`의 `asyncio.server`.
- `ChibiBroadcaster` 싱글톤(`get_broadcaster()`) — WS 서버와 `server.py` 도구가 공유. `set_action_handler(handler)`가 seam: `server.py`가 import 시 `_handle_window_action`을 꽂는다.
- **서버→클라이언트** 메시지 타입: `state`, `say`, `slice`, `sound`. **클라이언트→서버**: `say`, `tool_call`, `action`.
- `_state_push_loop`: `STATE_PUSH_INTERVAL_SECONDS = 2.0`마다 스냅샷 브로드캐스트.
- 도구는 `_fire_and_forget(broadcaster.broadcast({...}))`로 창에 이벤트 푸시. `_PENDING_TASKS`에 강한 참조 유지(GC 방지).
- 창 툴바 버튼(pull_gacha/set_active_* 등)은 `action` 메시지로 들어와 `_handle_window_action`으로 라우팅 → 창이 state.json을 직접 안 고치고 같은 검증된 도구 경로 재사용.

> WS 주소/메시지 타입은 server-rs에도 복제 → 바꾸면 surface-sync에 통보.

## 창 subprocess (`server.py` `open_pet_window`)

- 검증(캐릭터/에셋/옵션/`_window_runtime_issue`: tkinter+DISPLAY) 후 `_kill_existing_window()`(`~/.chibi-mcp/window.pid`의 PID에 SIGTERM), 로그 열고, 고유 `window-ready-<uuid>.json` ready-file 경로 생성, `subprocess.Popen([sys.executable, "-m", "chibi_mcp.window", "--image", ..., "--ws", ws://..., "--initial-state", <json>, "--ready-file", ...])`.
- **detached**: POSIX `start_new_session=True`, Windows `CREATE_NEW_PROCESS_GROUP`. stdout/stderr는 `window.log`로.
- `_window_startup_failure`가 ready-file을 최대 5초 폴링해 Tk 기동 확인 후 PID를 `window.pid`에 기록.
- `__main__._ensure_ws_server_for_open`: WS 포트가 안 살아있으면 detached `python -m chibi_mcp --ws-only` 스폰.
- 입력 하드닝: `_CHAR_ID_RE = ^[a-z][a-z0-9_]{0,40}$`, `_sanitize_say`(≤200자, 제어문자·개행 제거), `_resolve_catalog_image`(경로 탈출 방지).

## 창 내부 (`window.py`) — 크로스플랫폼 핵심

- **독립 프로세스.** WS로만 통신(파일/stdin 아님). `runtime.runtime_file`만 import — 나머지 패키지와 디커플.
- 클래스: `PetWindow`(컨트롤러, ~1,950줄), `ChibiBubble`, `ChibiButton`, `ChibiStatusCard` (모두 canvas 직접 드로잉).
- 렌더: Pillow로 `<stem>_<mood>.png` 변형 우선, 없으면 `_apply_mood_filter()`(`MOOD_FILTERS` 밝기/채도/틴트), `_apply_option_layers()`로 옵션 PNG 알파 합성. 캐시.
- 모션: idle bob(~0.6Hz sine), 무드별 FX 파티클, squish/slice/sparkle/jiggle/pull-reveal.
- **macOS PyObjC 투명화는 죽어있다.** `_macos_make_transparent()`는 항상 `False`(일부 Homebrew Python/Tk/PyObjC가 네이티브 세그폴트). 모든 플랫폼이 `overrideredirect(True)` 프레임리스 패널 사용. **되살리지 마라.** `server_window_smoke.py`가 로그에 `_objc`가 없는지 회귀 검사.
- **사운드 크로스플랫폼 분기**(`_play_sound`): darwin `afplay`, win32 `winsound`, linux `paplay`→`aplay` 폴백. WAV는 `~/.chibi-mcp/sounds/`에 synth 생성, `SOUND_VERSION` 버전.
- 키바인딩은 `<Command-*>`(mac) + `<Control-*>`(linux/win) 둘 다 바인드.
- 프리퍼런스: `~/.chibi-mcp/window-prefs.json`.

## 작업 후 국소 검증

```bash
cd server
python -m ruff check .
python -m pytest -q              # 전체
python -m pytest -q tests/test_state.py   # 국소
python -m chibi_mcp --check      # 에셋/런타임 자기진단
```
전체 게이트(`make check`)는 verifier 담당. 너는 국소 확인만 하고 넘긴다.

## 테스트 관례 (`server/tests/`)

`asyncio_mode = "auto"`, `testpaths = ["tests"]`. 도구/상태 변경 시 대응 테스트(test_server / test_state / test_gacha / test_ws_integration 등) 갱신. ruff: line-length 100, py312, select `E,F,W,I,UP,B,C4,SIM,RUF`, ignore `E501,SIM117`.
