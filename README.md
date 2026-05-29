# chibi-mcp

[![CI](https://github.com/soccz/chibi-mcp/actions/workflows/build.yml/badge.svg)](https://github.com/soccz/chibi-mcp/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![No telemetry](https://img.shields.io/badge/telemetry-none-blue.svg)](SECURITY.md)

`chibi-mcp` adds a local desktop pet, **chibi**, to Claude Code, Codex, and VS Code. It reacts to CPU/RAM/battery/idle state, tracks coding-session rhythm, collects characters, applies free visual option layers, and can be opened from an MCP client.

It is local-first: no telemetry, localhost WebSocket by default, open-source code, and `chibi-mcp --check` for install diagnostics.

<p align="center">
  <img src="assets/social-preview.png" alt="chibi-mcp social preview showing the local MCP pet for Claude Code, Codex, and VS Code" width="720">
</p>

## What You Get

- A local MCP server for Claude Code and Codex.
- A floating desktop pet window for Linux, macOS, and Windows desktop sessions.
- A VS Code sidebar extension packaged as a `.vsix`.
- 8 starter characters and 12 free option layers.
- Gacha, inventory, rename, active character, and option selection tools.
- Mood based on CPU, RAM, battery, and idle time.
- Slice cycle: every N tool calls, chibi gets sliced.
- `chibi-say`, a tiny CLI for making the pet show speech bubbles from scripts.

The base product is free. Monetization is not enabled: no paid packs, no paid random pulls, no Sponsors tiers, no license keys, and no team pricing unless explicitly approved later.

## Who It Is For

- Individual Claude Code/Codex users who want a local AI coding companion.
- VS Code users who want a sidebar pet and small save/task/debug reactions.
- Teams evaluating no-telemetry coding rituals, release mascots, or private character packs.
- Creators who want to submit rights-clean character or option packs.
- Devtool, keyboard, hackathon, or coding-stream communities exploring free collaboration drops.

Commercial readiness is documented without enabling payment: see [docs/PRODUCT_MARKET_READINESS.md](docs/PRODUCT_MARKET_READINESS.md), [docs/TEAM_ADOPTION.md](docs/TEAM_ADOPTION.md), and [docs/PILOT_PLAYBOOK.md](docs/PILOT_PLAYBOOK.md).

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
/chibi
내 치비 보여줘
```

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
내 치비 보여줘
치비 뽑기 한 번
치비 보관함 열어
```

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

See [INSTALL.md](INSTALL.md) for the full Claude/Codex/VS Code and Linux/macOS/Windows install matrix.

## Verify Install

Run either command:

```bash
chibi-mcp --check
chibi-check
```

Expected output includes:

- `ok: true`
- package version
- asset directory
- catalog count
- option count
- `tkinter: true` if the floating window can open

If `tkinter` is false or no display session is available, MCP tools still work, but the floating pet window will return a diagnostic instead of opening.

## Use It

### Common Prompts

```text
내 치비 보여줘
뽑기 한 번
보관함 열어
조청 드립 옵션 적용해줘
옵션 해제해줘
10번 호출마다 잘리게 해줘
```

### Main MCP Tools

| Tool | What it does |
|---|---|
| `open_pet_window` / `close_pet_window` | Open or close the floating pet |
| `get_pet_state` | Mood, system metrics, counters, active character |
| `pet_say(text)` | Show a short speech bubble |
| `slice_now` | Trigger a slice immediately |
| `set_slice_interval(n)` | Change the slice cadence |
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
```

It sends a local WebSocket message to the running chibi server. If nothing is running, it exits quietly, so it is safe inside scripts.

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

Claude Code hooks and the VS Code extension already use this bridge for small reaction bubbles.

## Visual Assets

<p align="center">
  <img src="docs/screenshots/starter-lineup.png" alt="chibi-mcp starter character lineup" width="720">
</p>

<p align="center">
  <img src="docs/screenshots/option-showcase.png" alt="chibi-mcp free option layers including syrup, glaze, powder, seeds, petals, resin stars, and sauce" width="720">
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

Install tkinter on Ubuntu/Debian:

```bash
sudo apt-get install -y python3-tk
```

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

## Not Affiliated With Anthropic

`chibi-mcp` is an independent open-source project. The `claude` CLI and MCP are Anthropic technologies; this project is not endorsed by Anthropic.

## License

Code is MIT. Official artwork and project presentation have separate usage terms
in [OFFICIAL_ASSET_TERMS.md](OFFICIAL_ASSET_TERMS.md). Asset provenance and pack
submission rules are documented in [ASSET_RIGHTS.md](ASSET_RIGHTS.md).
