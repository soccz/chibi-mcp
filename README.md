# chibi-mcp

[![CI](https://github.com/soccz/chibi-mcp/actions/workflows/build.yml/badge.svg)](https://github.com/soccz/chibi-mcp/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![No telemetry](https://img.shields.io/badge/telemetry-none-blue.svg)](SECURITY.md)

`chibi-mcp` adds a local desktop pet, **chibi**, to Claude Code, Codex, and VS Code that turns your machine's own state — CPU, RAM, battery, idle — into a character's mood. Other coding pets animate what your *agent* is doing; **chibi shows how your *machine* is doing** — then lets you collect characters and apply free visual layers across a coding session.

It is local-first: no telemetry, localhost WebSocket by default, open-source code, and `chibi-mcp --check` for install diagnostics.

<p align="center">
  <img src="assets/social-preview.png?v=1.4.39-chibi" alt="chibi-mcp social preview showing the local MCP pet for Claude Code, Codex, and VS Code" width="720">
</p>

<p align="center">
  <img src="docs/demo.gif?v=1.4.39-chibi" alt="animated chibi-mcp demo showing install commands, local status, and the floating pet window" width="720">
</p>

> **Public beta** — free installs and permissioned pilots. Maintainer release steps live in [For maintainers](#for-maintainers); the go/no-go checklist is in [docs/PUBLIC_BETA_READINESS.md](docs/PUBLIC_BETA_READINESS.md).

## Why chibi is different

Most desktop pets just animate a character, and agent overlays mirror what your AI is typing. chibi reflects **your own machine** — CPU, RAM, battery, idle — and your **coding-session rhythm**, as a collectible character with local ASMR-style sounds and a Korean dessert / artisan-keycap aesthetic.

| | chibi | Typical desktop pets (e.g. Shimeji) | Agent-activity overlays |
|---|---|---|---|
| Mood driven by your machine (CPU/RAM/battery/idle) | ✅ | ❌ | ❌ |
| Reacts to Claude/Codex tool-call rhythm | ✅ | ❌ | ⚠️ partial |
| Collect characters + free option layers | ✅ | ⚠️ skins only | ❌ |
| Local ASMR-style sounds (generated, no download) | ✅ | ❌ | ❌ |
| MCP-native across Claude Code / Codex / VS Code | ✅ | ❌ | ⚠️ varies |
| No telemetry · localhost-only · open source | ✅ | ⚠️ varies | ⚠️ varies |
| One-command install across three clients | ✅ | ❌ | ⚠️ varies |

The trends chibi builds on — slime ASMR, Korean artisan keycaps, chibi style — are cited with sources in [SPEC.md](SPEC.md).

## What You Get

- A local MCP server for Claude Code and Codex.
- A floating desktop pet window for Linux, macOS, and Windows desktop sessions.
- A VS Code sidebar extension packaged as a `.vsix`.
- 8 starter characters available now — 29 total, more dropping soon — plus 12 free option layers.
- Gacha, inventory, rename, active character, and option selection tools.
- Floating-window controls for inventory, option customization, gacha pulls,
  settings, size, connection status, and close actions.
- Mood based on CPU, RAM, battery, and idle time.
- Session cadence: Claude/Codex tool calls move the rhythm meter; every N calls,
  chibi plays a small milestone animation.
- `chibi-say`, a tiny CLI for making the pet show speech bubbles from scripts.
- Built-in local ASMR-style sounds for squish, milestone events, gacha pulls,
  rare pulls, option changes, and speech bubbles.

The base product is free. Monetization is not enabled: no paid packs, no paid random pulls, no Sponsors tiers, no license keys, and no team pricing unless explicitly approved later.

Sounds are also part of the free base product. The app generates short local
`.wav` files in `~/.chibi-mcp/sounds/`; no sound assets are downloaded at
runtime and no sound gacha is enabled.

## What It Does While Running

| Local signal | chibi reaction |
|---|---|
| CPU 80%+ | `헐떡` mood, warmer stage, panting accents |
| Battery under 20% while unplugged | `졸림` mood, slower bob, drowsy marks |
| Recent Claude/Codex tool call | `신남` mood, rhythm progress, optional bubble |
| 30 minutes idle | `시무룩` mood, quieter idle bubble |
| Every N tool calls | slice/milestone animation |

Gacha refill is free and local: the first pull each calendar day is free, then
you get +1 ticket per 100 captured tool calls and +1 ticket per 10 rhythm
slices. Claude Code plugin hooks record every `PostToolUse` event; bubbles are
still throttled so the pet does not talk on every command.

## Client Previews

<p align="center">
  <img src="docs/screenshots/claude-code.png?v=1.4.39-chibi" alt="chibi-mcp Claude Code preview with local floating pet window" width="720">
</p>

<p align="center">
  <img src="docs/screenshots/codex-terminal.png?v=1.4.39-chibi" alt="chibi-mcp Codex terminal preview with local diagnostics and floating pet" width="720">
</p>

<p align="center">
  <img src="docs/screenshots/vscode-sidebar.png?v=1.4.39-chibi" alt="chibi-mcp VS Code sidebar preview with status meters and floating pet" width="720">
</p>

## Who It Is For

- Individual Claude Code/Codex users who want a local AI coding companion.
- VS Code users who want a sidebar pet and small save/task/debug reactions.
- Teams evaluating no-telemetry coding rituals, release mascots, or private character packs.
- Creators who want to submit rights-clean character or option packs.
- Devtool, keyboard, hackathon, or coding-stream communities exploring free collaboration drops.

Commercial readiness is documented without enabling payment: see [docs/PRODUCT_MARKET_READINESS.md](docs/PRODUCT_MARKET_READINESS.md), [docs/PUBLIC_BETA_READINESS.md](docs/PUBLIC_BETA_READINESS.md), [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md), [docs/TEAM_ADOPTION.md](docs/TEAM_ADOPTION.md), and [docs/PILOT_PLAYBOOK.md](docs/PILOT_PLAYBOOK.md).

## Requirements

- Python 3.12+
- `pipx`
- Claude Code, Codex, or VS Code depending on your client
- A real desktop session for the floating pet window
- Python `tkinter` support for the floating window

On Ubuntu/Debian:

```bash
sudo apt-get install -y python3-tk
```

If you use pyenv Python, install `tk-dev` first, then rebuild that Python version.

## Install

The one-command installers below set up the MCP server and register it with your client. The server is also published on PyPI — `pipx install chibi-mcp` — for manual or CI setups (see [INSTALL.md](INSTALL.md)).

### Claude Code

Linux/macOS:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.sh)
```

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.ps1 | iex"
```

Then in Claude Code:

```text
/chibi-mcp:chibi
/chibi-mcp:chibi 뽑기
/chibi-mcp:chibi 보관함
```

If Claude replies `Please run /login` or `API Error: 401 Invalid authentication
credentials`, Claude Code failed authentication before the chibi command could
run. Run `/login` in Claude Code, then retry `/chibi-mcp:chibi`. To verify the
local pet without Claude authentication, run `chibi-mcp --check` and
`chibi-mcp --open` in a terminal. `--open` starts the local WebSocket helper
when needed, so toolbar actions like pull/options can work outside Claude too.
To check Claude, Codex, VS Code, MCP registration, and the local runtime
together, run `chibi-mcp --doctor`. The diagnostic separates `usable_clients`
from optional missing clients, so a working Claude install does not look broken
just because Codex or VS Code is not configured.

### Codex

Linux/macOS:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-codex.sh)
```

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-codex.ps1 | iex"
```

Then ask Codex:

```text
chibi 보여줘
chibi 뽑기 한 번
chibi 보관함 열어
chibi 꿀 글레이즈 옵션 적용해줘
```

If Codex reports a login/authentication error before it can use the MCP server,
run `codex login`, then retry. `chibi-mcp --doctor` reports Codex auth and MCP
registration separately from the local chibi runtime.

### VS Code

Linux/macOS:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-vscode.sh)
```

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-vscode.ps1 | iex"
```

Manual `.vsix` install:

```bash
code --install-extension chibi-mcp-*.vsix
```

Open the `chibi` activity bar view in VS Code after install.

If the activity bar view is missing, run `code --list-extensions` and confirm
`soccz.chibi-mcp` is listed. `chibi-mcp --doctor` includes this check when the
server CLI is installed.

See [INSTALL.md](INSTALL.md) for the full Claude/Codex/VS Code and Linux/macOS/Windows install matrix.

## Verify Install

Run either command:

```bash
chibi-mcp --check
chibi-mcp --doctor
chibi-check
```

Expected output includes:

- `ok: true`
- package version
- asset directory
- catalog count
- option count
- `tkinter: true` if the floating window can open
- `clients` from `--doctor`, including Claude auth, Codex auth, MCP registration, and VS Code extension visibility
- `ready: true` from `--doctor` only when the local runtime and every detected client path are ready

If `tkinter` is false or no display session is available, MCP tools still work, but the floating pet window will return a diagnostic instead of opening.
If `ok` is true but `ready` is false, chibi itself is installed; follow the
printed `next_steps` for Claude login, Codex login/MCP registration, or VS Code
extension visibility.

## Use It

### Common Prompts

```text
chibi 보여줘
chibi 뽑기 한 번
chibi 보관함 열어
꿀 글레이즈 옵션 적용해줘
옵션 해제해줘
10번 호출마다 마일스톤 반응하게 해줘
```

### Main MCP Tools

| Tool | What it does |
|---|---|
| `open_pet_window` / `close_pet_window` | Open or close the floating pet |
| `get_pet_state` | Mood, system metrics, counters, active character |
| `pet_say(text)` | Show a short speech bubble |
| `slice_now` | Trigger the milestone animation immediately |
| `set_slice_interval(n)` | Change the milestone cadence |
| `pull_gacha` | Pull one character |
| `get_inventory` | Show owned characters and ticket balance |
| `set_active_character(id)` | Switch active character |
| `get_options` | List free visual option layers |
| `set_active_options([ids])` / `clear_active_options` | Apply or clear up to 3 option layers |
| `rename_character(id, nickname)` | Rename a character you own |

## `chibi-say`

The Python package also installs `chibi-say`:

```bash
chibi-say "build done"
chibi-say "tests failed"
chibi-say --tool-call "tests green"
```

It sends a local WebSocket message to the running chibi server. Plain
`chibi-say` only shows a bubble; `--tool-call` also advances rhythm/tickets.
If nothing is running, it exits quietly, so it is safe inside scripts.

Examples:

```bash
# Git post-commit hook
chibi-say "commit!"

# Makefile
build:
	npm run build && chibi-say "build done" || chibi-say "build failed"

# CI/local test wrapper
./run_tests.sh && chibi-say "tests green" || chibi-say "tests red"
```

Claude Code hooks use `chibi-say --tool-call` on `PostToolUse` so real tool
calls feed mood, rhythm, slices, and tickets. VS Code uses the same local
bridge for save/task/debug reactions.

## Visual Assets

<p align="center">
  <img src="docs/screenshots/starter-lineup.png?v=1.4.39-chibi" alt="chibi-mcp starter character lineup" width="720">
</p>

<p align="center">
  <img src="docs/screenshots/option-showcase.png?v=1.4.39-chibi" alt="chibi-mcp free option layers including amber glaze, honey glaze, powder, seeds, petals, resin stars, and sauce" width="720">
</p>

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for the full Claude Code, Codex, VS Code, Linux, macOS, and Windows troubleshooting guide.

### `chibi-mcp` was installed but the command is not found

Run:

```bash
pipx ensurepath
```

Then restart your terminal.

### Floating window does not open on Linux

Check:

```bash
chibi-mcp --check
echo "$DISPLAY"
echo "$WAYLAND_DISPLAY"
```

Test the actual floating window outside Claude/Codex:

```bash
chibi-mcp --open
chibi-mcp --open --view-mode debug
```

Install tkinter on Ubuntu/Debian:

```bash
sudo apt-get install -y python3-tk
```

On macOS Homebrew Python 3.14, if `python3 -m tkinter` says `_tkinter` is missing:

```bash
brew install python-tk@3.14
pipx uninstall chibi-mcp || true
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
chibi-mcp --check
```

The Claude/Codex one-command installers now attempt this macOS Tk repair automatically and re-run `chibi-mcp --check`.

Linux installers also attempt Tk repair through common package managers, and Windows PowerShell installers can bootstrap Python/pipx before running the same health check.

### VS Code `code` command is missing

In VS Code, run:

```text
Shell Command: Install 'code' command in PATH
```

Then retry the VS Code installer.

### Claude or Codex does not see the server

Register manually:

```bash
claude mcp add chibi -- chibi-mcp
codex mcp add chibi -- chibi-mcp
```

If Claude still prints `Unknown command: /chibi` or routes `/chibi-mcp:chibi`
to an old command, rerun the Claude installer and restart Claude Code:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.sh)
```

If the command replies but no window appears, run `chibi-mcp --open` in a
terminal. It starts a local `chibi-mcp --ws-only` helper if no WebSocket server
is already listening, then prints the direct window result and log paths for
`~/.chibi-mcp/window.log` and `~/.chibi-mcp/ws.log`.

## Creator Packs

Creator/team pack tooling is included, but paid packs are not enabled.

```bash
chibi-pack init ./my-pack
chibi-pack validate ./my-pack
chibi-pack preview ./my-pack
```

Before a public pack proposal, fill in the rights metadata, then run:

```bash
chibi-pack validate --submission ./my-pack
```

Public submissions now require complete rights metadata: `license`, `source_rights`, `rights_owner`, `asset_origin`, `permission_scope`, and `no_third_party_ip: true`.

Runnable examples from a clone:

```bash
chibi-pack validate examples/packs/spring-hwajeon
chibi-pack validate examples/packs/team-sprint
```

See [docs/CREATOR_PACKS.md](docs/CREATOR_PACKS.md).

## Privacy And Trust

- No telemetry.
- Localhost WebSocket by default.
- Local state under the user profile.
- `chibi-audit` prints the local trust report.
- No paid gates or license keys.
- Security reports: see [SECURITY.md](SECURITY.md).
- Official asset terms: see [OFFICIAL_ASSET_TERMS.md](OFFICIAL_ASSET_TERMS.md).
- Brand/fork naming: see [TRADEMARK.md](TRADEMARK.md).
- Asset, pack, and copycat response: see [ASSET_RIGHTS.md](ASSET_RIGHTS.md),
  [docs/IP_AND_RIGHTS.md](docs/IP_AND_RIGHTS.md), and
  [docs/COPYCAT_RESPONSE.md](docs/COPYCAT_RESPONSE.md).

```bash
chibi-audit
```

## For Contributors

From a clone:

```bash
make check
```

Strict desktop runtime check:

```bash
xvfb-run -a make runtime-check
```

GitHub Actions verifies:

- Python on Linux, macOS, and Windows
- Windows PowerShell installer syntax
- VS Code `.vsix` packaging
- desktop smoke builds on Linux, macOS, and Windows
- Rust/Tauri formatting and linting
- tagged release checksums

Useful docs:

- [INSTALL.md](INSTALL.md) — full install matrix
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — install and runtime fixes
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution guide
- [ASSET_RIGHTS.md](ASSET_RIGHTS.md) — official asset and pack provenance policy
- [OFFICIAL_ASSET_TERMS.md](OFFICIAL_ASSET_TERMS.md) — official artwork usage terms
- [TRADEMARK.md](TRADEMARK.md) — brand and fork naming guardrails
- [COMMERCIAL_STRATEGY.md](COMMERCIAL_STRATEGY.md) — expansion readiness and deferred monetization guardrails
- [docs/PRODUCT_MARKET_READINESS.md](docs/PRODUCT_MARKET_READINESS.md) — commercial readiness scorecard
- [docs/TEAM_ADOPTION.md](docs/TEAM_ADOPTION.md) — team/admin evaluation guide
- [docs/PILOT_PLAYBOOK.md](docs/PILOT_PLAYBOOK.md) — free pilot feedback loop
- [GITHUB_STAR_STRATEGY.md](GITHUB_STAR_STRATEGY.md) — launch and repository growth plan
- [docs/LAUNCH_KIT.md](docs/LAUNCH_KIT.md) — launch/distribution copy

## For maintainers

Preflight before a release tag (under a virtual display if headless):

```bash
xvfb-run -a make public-beta-check
```

Release-tag preflight after pushing `main`:

```bash
make release-check TAG=v1.4.39
```

See [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md) for tagging and [docs/PUBLIC_BETA_READINESS.md](docs/PUBLIC_BETA_READINESS.md) for the go/no-go checklist.

## Not Affiliated With Anthropic

`chibi-mcp` is an independent open-source project. The `claude` CLI and MCP are Anthropic technologies; this project is not endorsed by Anthropic. **chibi** is an independent original character series and is not Anthropic's Claude mascot.

## License

Code is MIT. Official artwork and project presentation have separate usage terms
in [OFFICIAL_ASSET_TERMS.md](OFFICIAL_ASSET_TERMS.md). Asset provenance and pack
submission rules are documented in [ASSET_RIGHTS.md](ASSET_RIGHTS.md).

`chibi` and `chibi-mcp` are unregistered (common-law) trademarks of this project; see [TRADEMARK.md](TRADEMARK.md) for brand and fork-naming guidance.
