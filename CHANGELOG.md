# Changelog

All notable changes to chibi-mcp. Format: keep-a-changelog inspired, but condensed.

## Unreleased

Commercial-readiness polish without enabling paid gates.

- Replaced the floating window's black fallback surface with a light panel and
  fixed the macOS transparency helper so chibi does not appear inside a black box.
- Added floating-window controls for inventory, option customization, gacha
  pulls, and close actions, routed through localhost WebSocket actions back to
  the MCP server instead of writing state directly.
- Fixed the Claude slash command instructions so `/chibi-mcp:chibi 뽑기` handles arguments directly instead of trying to call an unknown `/chibi` command.
- Claude installers now force a clean plugin refresh with `uninstall --keep-data`
  before reinstalling, so same-version cached command files cannot keep routing
  `/chibi-mcp:chibi` through stale `/chibi` instructions.
- Added a deterministic `chibi-share --static-demo` mode for committed launch
  images so release verification is not affected by live local system mood.
- Replaced the FastMCP stdio startup path with a small JSON-RPC stdio loop for
  Claude Code, preventing banner/log output and transport hangs from surfacing
  as `Failed to connect`.
- MCP stdio now reads and writes UTF-8 bytes directly so Korean catalog/tool
  responses work on Windows consoles as well as Linux/macOS.
- Claude/Codex installers now force `pipx` to reinstall from the GitHub server
  subdirectory, avoiding stale installs that report old versions such as 1.1.0
  as already latest.
- Tk repair paths and troubleshooting docs now use the same GitHub force
  reinstall command instead of plain pipx reinstall/upgrade, so recovery
  cannot return to an old package source.
- Added `chibi-mcp --open` for direct floating-window testing outside
  Claude/Codex, and made slash-command failure guidance surface the exact
  runtime reason/log path instead of falling through to gacha.
- Claude/Codex installers now refresh the MCP registration after installing so
  stale client entries cannot keep pointing at an old or broken command.
- The floating window now explicitly places and raises itself after Tk layout,
  reducing macOS cases where the window process starts but the pet is not
  visible.
- Disabled PyObjC macOS transparency by default and removed the PyObjC runtime
  dependency, avoiding native `_objc` segmentation faults on Homebrew Python
  3.14 + Tk 9. The stable default is now the Tk light-panel window.
- Added a cross-platform Tk window ready-file handshake. `open_pet_window` now
  waits for the child process to finish Tk startup before returning
  `opened: true`, and reports timeout/early-exit logs consistently on macOS,
  Linux, and Windows.
- Strengthened floating-window and VS Code action button styling with clearer
  primary, secondary, selected, and close states.
- Expanded built-in local ASMR-style sounds: squish, slice, normal gacha, rare gacha, option brush, and bubble pop are generated as free local wav files with no network or paid sound packs.
- Expanded installer self-repair beyond macOS: Linux bash installers now try Tk repair across `apt`, `dnf`, `yum`, `pacman`, `zypper`, and `apk`; Windows PowerShell installers can bootstrap Python with `winget` before installing `pipx`.
- Made the Claude/Codex installers more self-healing: they install `pipx` when it is missing, suppress confusing `pipx ensurepath` noise, attempt macOS Homebrew Tk repair automatically in bash, reinstall the pipx app after Tk repair, and re-run the health check.
- Added macOS Homebrew Python Tk troubleshooting for `_tkinter` import failures, including Python 3.14 `python-tk@3.14` guidance.
- Claude/Codex install scripts now warn when `chibi-mcp --check` reports `tkinter: false` and print the matching Linux/macOS repair commands.
- Replaced remaining non-ASCII name spelling in README, plugin metadata, command examples, installer output, and server descriptions with the ASCII `chibi` brand spelling.
- Extended the brand identity sanity check so legacy project names and non-ASCII `chibi` spellings cannot leak back into public files.
- Added product-market readiness, team adoption, and pilot playbook docs to clarify commercial gaps before paid launch.
- Added team pilot and collaboration/drop issue forms for structured free feedback and partner ideas.
- `chibi-audit` now reports commercial readiness docs/templates and confirms monetization remains disabled.
- Added official asset usage terms, trademark/fork naming guardrails, and a copycat response playbook.
- Added an IP/rights concern issue form for copied assets, confusing forks/listings, and risky pack submissions.
- `chibi-pack validate --submission` now requires `rights_owner`, `asset_origin`, `permission_scope`, and `no_third_party_ip: true` in addition to `license` and `source_rights`.
- Official and sample asset manifests now include expanded provenance metadata.
- GitHub Releases now attach `SHA256SUMS.txt` for release artifact verification.
- CI now parses Windows PowerShell installer scripts on `windows-latest`.
- Added `docs/TROUBLESHOOTING.md` for Claude Code, Codex, VS Code, Linux, macOS, and Windows install/runtime fixes.
- Added a feature request issue form with no-telemetry, no-paid-gate, and cross-platform guardrails.
- Added Windows PowerShell installers for Claude Code, Codex, and VS Code.
- Added Linux/macOS VS Code `.vsix` installer script.
- CI now runs Python tests on Linux, macOS, and Windows, and packages the VS Code `.vsix` on every push/PR.
- Added runnable creator/team sample packs under `examples/packs/`.
- Added `docs/CREATOR_PACKS.md` and `docs/LAUNCH_KIT.md` for creator submissions, team pack positioning, and launch channel readiness.
- Added `ASSET_RIGHTS.md` and `docs/IP_AND_RIGHTS.md` for asset provenance, copycat response, and rights-review guardrails.
- `chibi-pack validate --submission` now requires `license` and `source_rights` metadata for public pack submissions.
- `verify_all.sh` and tests now validate the sample packs in submission mode.

## v1.4.4 — 2026-05-29

Broader free option catalog for a more commercial-looking character platform.

- Expanded the free option catalog from 4 to 12 transparent PNG layers: condensed milk, kinako, black sesame, red bean, petals, resin stars, matcha, and spicy sauce.
- Updated the root, packaged server, and VS Code asset catalogs so Claude/Codex/VS Code all see the same options.
- `chibi-share --preset options` now renders a 12-item grid instead of a 4-card showcase.
- VS Code extension assets/version moved to 0.5.2.
- Tests now require at least 12 packaged free options and verify their PNGs are present.

## v1.4.3 — 2026-05-29

Free visual option layers for higher character completeness.

- Added honey, jocheong, sugar bead, and rainbow sprinkle transparent option PNGs.
- Added MCP tools: `get_options`, `set_active_options`, and `clear_active_options`.
- Floating pet window now composites up to three active option layers over the base character.
- VS Code extension 0.5.1 shows option toggles and overlays option PNGs on the active pet.
- `chibi-share --preset options` generates a 1600x900 option showcase image.
- Pack validation and previews now support top-level `options[]` entries.

## v1.4.2 — 2026-05-29

Launch visual polish using the provided PNG character assets.

- `chibi-share --preset lineup` generates a 1600x900 starter lineup image from the local catalog.
- README now shows generated social preview and starter lineup assets above install instructions.
- `verify_all.sh` now checks committed launch image assets and lineup share-card generation.

## v1.4.1 — 2026-05-29

Commercial helper polish.

- `chibi-pack init` scaffolds a starter creator/team pack with `meta.json` and a placeholder PNG.
- `chibi-pack validate` rejects explicit image paths that escape the pack directory.
- `chibi-share --preset social-preview` generates a 1280×640 GitHub social preview card.
- `verify_all.sh` now smoke-tests `chibi-audit`, `chibi-pack init/validate/preview`, and both share-card presets.

## v1.4.0 — 2026-05-29

Commercial-readiness surfaces without paid gates.

- New `chibi-audit` CLI: local trust report covering no telemetry, localhost default, state path, asset catalog, entry points, and hook/plugin files.
- New `chibi-pack` CLI: validate creator/team character packs and write static HTML previews.
- New `chibi-share` CLI: generate a 1080×1080 local session share card PNG.
- README, commercial strategy, and GitHub star strategy now point to executable share/pack/trust commands.

## v1.3.3 — 2026-05-29

Final v1.3 audit gaps.

- VS Code daily save reward no longer grants duplicate tickets.
- VS Code webview escapes nickname/alt text before rendering.
- `CHIBI_WS_PORT` invalid values fall back consistently across stdio/WS modes.
- `verify_all.sh` checks shell syntax and compiles `scripts/rotate-hmac.py`.
- `rotate-hmac.py --apply` is disabled until a user-approved paid entitlement gate exists.
- Branch desktop CI now uses `tauri build --debug --no-bundle`; tag builds still produce installers.

## v1.3.2 — 2026-05-29

Audit follow-up polish.

- WS reconnect: exponential backoff (1s → 30s cap, ×1.7) instead of fixed 2s; resets on successful connect.
- WS drops now log at debug (json parse error vs queue full with current size) instead of bare suppress.
- `MOOD_FILTERS` schema documented inline.
- `skills/chibi/SKILL.md`: documents the exact `pull_gacha` success / failure response shape; clarifies catalog vs inventory roles.
- `tests/test_gacha.py`: +2 regression tests for the v1.3.1 defer-save refactor.
- README "Client Paths" reframed to match the actual Python tk window path (Tauri marked archived).

## v1.3.1 — 2026-05-29

Final review pass — 12 confirmed fixes from a 20-loop multi-agent audit (110 subagents, 50 raw → 28 confirmed).

- VSCode gacha race: `_gachaInProgress` guard.
- `state.save()` now snapshots under the lock and writes outside it.
- `get_catalog` / `_check` JSON & I/O exception handling.
- `open_pet_window` log_fh always closed; subprocess inherits the fd.
- character_id path-traversal hardening (`^[a-z][a-z0-9_]{0,40}$` regex + `asset_root not in image_path.parents` check).
- Window `after()` callbacks tracked & cancelled on shutdown.
- `get_state` singleton init lock (TOCTOU).
- `CHIBI_WS_PORT` safe parsing (warn + fall back to default on invalid).
- `bin/chibi-react.sh` POSIX char class removed.
- Cohesion: removed duplicate `_seconds_until_local_midnight`; one canonical helper in state.py.

## v1.3.0 — 2026-05-29

Host-agnostic chibi-say bridge.

- VSCode extension 0.5.0: spawns `chibi-say` on save / task start·end / debug start·terminate. Setting `chibiMcp.sayBridge.enabled`.
- README "Anywhere" section: git post-commit, Makefile, CI, zsh `precmd` examples.
- MCP tools table refreshed (13 tools).

## v1.2.0 — 2026-05-29

Claude Code hooks bridge, PyObjC transparency, idle bubbles, mood variant loader.

- `ws_server` handles inbound `{type:say,text:...}`; new `chibi-say` & `chibi-check` CLIs.
- `hooks/hooks.json` + `bin/chibi-react.sh` for PreToolUse / PostToolUse.
- PyObjC real transparency on darwin (`pyobjc-framework-Cocoa` conditional dep).
- Per-mood PNG variant loader (`<id>_<mood>.png` if shipped).
- Idle bubbles every 4–7 minutes.

## v1.1.0 — 2026-05-28

Frameless transparent window, idle bob, sound effects.

- `overrideredirect(True)` — no title bar.
- macOS `-transparent` + `systemTransparent` bg + `-alpha 0.96` fallback.
- Canvas-based render; bob via `canvas.coords`; ±4px / 0.6Hz.
- Procedurally-generated wavs (`bubble.wav`, `slice.wav`) at `~/.chibi-mcp/sounds/`. Playback via afplay / paplay·aplay / winsound.

## v1.0.0 — 2026-05-28

Live updates, real gacha, mood-tinted transparent window.

- Persistence at `~/.chibi-mcp/state.json` (inventory, tickets, active char, last free pull, total pulls).
- `pull_gacha`, `get_inventory`, `set_active_character`, `rename_character`, `add_ticket` MCP tools.
- Window subscribes to local WS for live state / slice / say events.
- Mood filter (brightness · saturation · tint) per Mood — 7 expressions from one base PNG.
- Speech bubble (4s) below the character.

## v0.5.0 — 2026-05-28

Floating tk window.

- `open_pet_window` / `close_pet_window` spawn a detached Python subprocess.
- `~/.chibi-mcp/window.pid` tracking.
- Mood label, drag, dbl-click squish, Esc / Cmd-W / right-click to close.

## v0.4.x — 2026-05-28

- v0.4.0: Freemium baseline — 8 free / 21 Pro placeholders, HMAC license verification (`license.py`), `get_license_status`, `get_catalog` tier filter, 37 tests.
- v0.4.1: 21 placeholder PNGs removed from the public repo (kept local-only).
- v0.4.2: `chibi` rebrand, `.claude-plugin/marketplace.json`, `/chibi` slash command.

## v0.3.0 — 2026-05-28

Reborn as a Claude Code plugin (`.claude-plugin/`, `skills/`, `.mcp.json`). Tauri desktop app moved to archival.

## v0.1.x / v0.2.x — earlier

Tauri attempts (`desktop/`). Deprecated mid-project due to macOS signing pain; kept under `desktop/` for reference.
