---
name: chibi-verify
description: chibi-mcp 검증 게이트 실행·해석법 — make check(=verify_all.sh 16섹션)·pytest·ruff·--check·plugin validate·strict-check, 표면 간 일관성(버전·도구목록·에셋동일성·브랜드) 교차 비교, 흔한 실패 원인. chibi-verifier가 변경을 검증할 때 사용. 점진적 QA와 최종 게이트 실행 시 반드시 적용.
---

# chibi-verify — 검증 게이트 가이드

검증의 핵심은 "파일 존재"가 아니라 **표면 간 일관성 교차 비교**다. 점진적으로(각 모듈 완료 직후) 돌리고 마지막에 전체 게이트.

## 점진적 QA (모듈별)

| 무엇이 끝났나 | 즉시 돌릴 검증 |
|--------------|---------------|
| core-dev 코어 변경 | `cd server && python -m ruff check . && python -m pytest -q` (+ 국소 테스트 파일) |
| core-dev 도구 추가 | 도구 등록 교차 비교(아래) + `python -m chibi_mcp --check` |
| surface-sync 전파 | 버전 4파일 일치 + meta.json 3중 동일성 + (도구목록 표면 일치) |
| docs-keeper 문서 | 브랜드 금칙어 스캔 + README 필수 신호 |
| 전체 완료 | `make check` (verify_all.sh 전체 16섹션) |

## 핵심 명령

```bash
# 가장 빠른 단위 (코어)
cd server && python -m ruff check . && python -m pytest -q

# 자기진단
cd server && python -m chibi_mcp --check
python -m chibi_mcp --doctor      # 클라이언트 등록/auth까지

# 전체 게이트 (정본)
make check                        # = ./scripts/verify_all.sh

# GUI 스모크 포함 (디스플레이/xvfb 필요)
make strict-check                 # = CHIBI_STRICT_RUNTIME=1 verify_all.sh

# 릴리스 전
make public-beta-check
make release-check TAG=vX.Y.Z
```

Makefile 타깃: `check`, `server-test`(ruff+pytest), `server-build`, `vscode-package`, `desktop-lint`, `rust-check`, `runtime-check`, `strict-check`, `public-beta-check`, `release-check`.

## verify_all.sh 16개 배너 섹션 (set -euo pipefail — 한 단계라도 실패면 중단)

스크립트의 `== ... ==` 배너 섹션은 **정확히 16개**이고, 마지막에 `all checks passed` 종결 echo가 찍힌다. (번호는 실패→원인 매핑에 쓰이므로 실제 섹션 순서와 맞춰둔다.)

1. **셸 스크립트**: `bash -n` 으로 `scripts/*.sh`+`bin/*.sh` 구문 검사
2. **PowerShell**: pwsh로 `scripts/*.ps1` 파싱 (pwsh 없으면 skip)
3. **Python** (server/): 버전 일치(`__version__`==pyproject==두 plugin.json) → `ruff check .` → `pytest -q` → 핵심 파일 `py_compile` → 휠 빌드 → `--check` → 상업 CLI 스모크(pack init/validate/preview, audit, share 4프리셋 **픽셀 크기 단언**)
4. **런치 이미지 에셋**: 필수 PNG 크기 단언 + share/social/lineup/options + 데모 스크린샷 재생성 후 커밋본과 픽셀 diff(stale이면 실패) + `docs/demo.gif` 960×540 ≥12프레임
5. **브랜드 정체성**: 레포 전체 레거시 금칙 브랜드 용어 스캔 + 공개 문서 표면 + `meta.json` 표시 필드
6. **인스톨러 self-heal**: install-claude/codex `.sh`/`.ps1`에 필수 self-heal/MCP-refresh 토큰 존재 + 금지된 stale pipx 명령 부재; install-vscode·공개문서 필수 문자열
7. **Claude 플러그인**: `claude plugin validate` (claude 없으면 skip, 20s)
8. **Codex 플러그인**: `codex plugin marketplace add` (codex 없으면 skip)
9. **Desktop 프런트엔드**: desktop/ `npm run lint`
10. **Rust MCP 프로토타입** (server-rs): `cargo fmt --check` + `cargo clippy --all-targets -D warnings` — **cargo 없으면 하드 실패**
11. **Tauri 데스크탑 Rust** (desktop/src-tauri): Linux 데스 있으면 `cargo fmt`+`cargo check`, 없으면 soft-skip (단 `CHIBI_STRICT_RUNTIME=1`이면 하드 실패)
12. **Python 창 런타임**: `tkinter` import; strict면 디스플레이 필요 + `window_ui_smoke.py`+`server_window_smoke.py`. (이 섹션 안에 Tauri 백엔드 `cargo fmt --check` 독립 재확인 블록이 함께 돈다 — 별도 배너 없음)
13. **VS Code 확장**: `npm run lint` + `npm run package`
14. **워크플로 sanity**: `build.yml`에 OS 매트릭스/잡/릴리스 토큰
15. **권리 정책**: 필수 권리 문서 + 모든 `meta.json`에 `no_third_party_ip: true`
16. **GitHub YAML**: `release.yml`+ISSUE_TEMPLATE js-yaml 검증

→ 종료 시 `all checks passed` echo.

## 표면 간 교차 비교 (verifier의 진짜 일)

단일 파일이 아니라 **두 표면을 동시에 읽어 shape 대조**:

- **버전**: 4파일(`__init__.py`/`pyproject.toml`/두 `plugin.json`)을 동시 grep → 모두 `1.4.39`인지. vscode(`0.5.3`)·rust(`0.2.0-alpha.1`)는 별도 라인이라 일치 대상 아님.
- **도구 목록**: `__main__.py`의 `_TOOL_FUNCTIONS` 16개 ↔ `server.py`의 `@mcp.tool()` ↔ `skills/chibi/SKILL.md` description 열거 ↔ `commands/chibi.md` 라우팅. 코어에 있는데 SKILL/commands에 없거나 그 반대면 드리프트.
- **에셋 동일성**: `assets/meta.json` = `server/chibi_mcp/assets/meta.json` = `vscode-ext/resources/meta.json` 가 byte-identical 인지 **`diff`/`md5sum`으로 직접 확인**한다. 주의: `test_option_assets.py`는 byte-identity를 강제하지 **않는다** — 자유 옵션 id 순서 + 권리 top-level 필드(`no_third_party_ip` 등) + 이미지 512×512 RGBA 규격만 대조한다. 따라서 한 사본의 `name_ko`/`category`/`description`이나 characters 배열만 바뀌면 테스트는 통과한다. byte-identity는 테스트가 아니라 diff로 검증하라.
- **브랜드**: 레포 전체에 레거시 금칙어 부재(5단계가 강제).

## 흔한 실패 원인 → 회부 대상

| 실패 | 원인 | 회부 |
|------|------|------|
| 버전 불일치(3단계) | 표면 하나만 범프 | surface-sync |
| 도구가 안 보임 | `_TOOL_FUNCTIONS` 누락 | core-dev |
| meta.json 자유옵션 id 불일치(test_option_assets) | 사본 하나만 수정 | surface-sync |
| 브랜드 금칙어(5단계) | 레거시명 노출 | docs-keeper 또는 surface-sync |
| 권리 필드 누락(15단계) | meta.json `no_third_party_ip` 빠짐 | surface-sync |
| ruff/pytest | 코드 결함 | core-dev |
| cargo 부재 하드 실패(10단계) | 환경에 Rust 없음 | **환경 skip 사유로 보고**(코드 결함 아님) |
| 창 스모크 실패 | 디스플레이 없음 | strict 아니면 skip 사유, strict면 core-dev |

## 보고 원칙

- 명령 + 실제 출력(실패 라인)을 함께 보고. 단정 금지.
- 환경 부재로 못 돈 단계(cargo/claude/pwsh/디스플레이)는 **skip 사유**로 명시 — 코드 실패와 구분.
- 직접 고치지 말고 책임 에이전트에 회부. `_workspace/05_verify_report.md`에 실행 명령/결과/회부 기록.
