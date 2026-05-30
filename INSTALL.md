# Install from GitHub

This repo supports three user-facing clients from the same GitHub source, across Linux, macOS, and Windows:

- Claude Code: MCP server plus Claude plugin commands.
- Codex: MCP server plus optional Codex plugin marketplace metadata.
- VS Code: downloadable `.vsix` from GitHub Releases.

## Platform matrix

| Platform | Claude Code | Codex | VS Code | Floating pet |
|---|---|---|---|---|
| Linux desktop | `install-claude.sh` | `install-codex.sh` | `install-vscode.sh` or `.vsix` | supported with `tkinter` + display session |
| Linux SSH/headless | MCP tools work | MCP tools work | remote/editor dependent | returns a clear desktop diagnostic |
| macOS | `install-claude.sh` | `install-codex.sh` | `install-vscode.sh` or `.vsix` | supported with Python `tkinter` |
| Windows PowerShell | `install-claude.ps1` | `install-codex.ps1` | `install-vscode.ps1` or `.vsix` | supported with Python `tkinter` |

## Prerequisites

- Python 3.12+
- `pipx` on your PATH
- A real desktop session if you want the floating pet window
- Python `tkinter` support for the floating window (`chibi-mcp --check` reports this). On Ubuntu/Debian system Python, install `python3-tk`; on macOS Homebrew Python, install the matching `python-tk@X.Y` package such as `python-tk@3.14`; for pyenv Python, install `tk-dev` and rebuild Python.
- `code` on PATH for the VS Code installer. In VS Code, run "Shell Command: Install 'code' command in PATH" if needed.

If an install path fails, use [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for client-specific fixes and the issue report checklist.

Typical `pipx` setup:

```bash
# Linux/macOS
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

```powershell
# Windows PowerShell
py -m pip install --user pipx
py -m pipx ensurepath
```

## One-command installs

### Linux/macOS

Claude Code:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.sh)
```

Codex:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-codex.sh)
```

VS Code:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-vscode.sh)
```

### Windows PowerShell

Claude Code:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.ps1 | iex"
```

Codex:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-codex.ps1 | iex"
```

VS Code:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-vscode.ps1 | iex"
```

The Claude/Codex scripts install `pipx` if needed, install or upgrade the `chibi-mcp` server, run `chibi-mcp --check`, then refresh the MCP server registration with the selected client. If Tk is missing, bash installers try platform repair: Homebrew `python-tk@X.Y` on macOS and common Linux package managers (`apt`, `dnf`, `yum`, `pacman`, `zypper`, `apk`). Windows PowerShell installers can bootstrap Python with `winget` before installing `pipx`, then warn if Tk support is still unavailable. The VS Code scripts download the latest `.vsix` from GitHub Releases and install it with `code --install-extension`.

After a Claude or Codex install, run this for a single cross-client report:

```bash
chibi-mcp --doctor
```

It separates local runtime issues from Claude auth, Codex auth, MCP
registration, and VS Code extension visibility.
`ok: true` means the local chibi runtime is healthy. `ready: true` means the
checked Claude, Codex, and VS Code paths are also ready. If an installer warns
that MCP registration failed, log in to that client and rerun
`chibi-mcp --doctor` before retrying the slash command.

## Manual server install

Install the MCP server directly from GitHub:

```bash
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
```

For upgrades from GitHub:

```bash
pipx uninstall chibi-mcp || true
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
```

If an older install was created from a stale package source, uninstall once and
install from GitHub again instead of using a plain `pipx upgrade`.

Verify the install:

```bash
chibi-mcp --check
chibi-mcp --doctor
```

Open the floating window directly, without Claude/Codex:

```bash
chibi-mcp --open
chibi-mcp --open --view-mode debug
```

On macOS, if `python3 -m tkinter` fails with `ModuleNotFoundError: No module named '_tkinter'`, install the matching Homebrew Tk package, then reinstall:

```bash
brew install python-tk@3.14
pipx uninstall chibi-mcp || true
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
chibi-mcp --check
```

The Claude/Codex bash installers do this macOS Tk repair automatically when possible. Set `CHIBI_SKIP_TK_REPAIR=1` before running the installer if you want a warning only.

## Codex

Register the MCP server:

```bash
codex mcp add chibi -- chibi-mcp
```

Optional plugin marketplace registration:

```bash
codex plugin marketplace add soccz/chibi-mcp
```

Then ask Codex:

```text
chibi 보여줘
chibi 뽑기 한 번
chibi 보관함 열어
```

If Codex reports a login/authentication error, run:

```bash
codex login
chibi-mcp --doctor
```

## Claude Code

Direct MCP registration:

```bash
claude mcp add chibi -- chibi-mcp
```

Plugin registration inside Claude Code:

```text
/plugin marketplace add soccz/chibi-mcp
/plugin marketplace update chibi-mcp
/plugin update chibi
/plugin install chibi@chibi-mcp
```

The plugin gives Claude the `/chibi-mcp:chibi` command and the `chibi` skill prompt. The MCP server must still be installed with `pipx` so the `chibi-mcp` command is available.

If `/chibi-mcp:chibi` replies `Please run /login` or `API Error: 401 Invalid
authentication credentials`, Claude Code is not authenticated and chibi has not
run yet. Run `/login` in Claude Code, then retry. To test the local install
without Claude authentication, run:

```bash
chibi-mcp --check
chibi-mcp --open
chibi-mcp --doctor
```

If `/chibi-mcp:chibi` still reports `Unknown command: /chibi`, the installed
Claude plugin is stale. Rerun the one-command installer; it updates the
marketplace and installed plugin, then restart Claude Code.

Try:

```text
/chibi-mcp:chibi
/chibi-mcp:chibi 뽑기
/chibi-mcp:chibi 보관함
```

When the Claude plugin is installed, `PostToolUse` hooks also feed chibi's
rhythm counter. The pet becomes `신남` after recent tool calls, slices every
configured interval, and grants gacha tickets after 100 captured tool calls or
10 slices. Restart Claude Code after install so the refreshed hook files are
loaded.

## VS Code

Download the latest `.vsix` from GitHub Releases, then run:

```bash
code --install-extension chibi-mcp-*.vsix
```

Open the `chibi` activity bar view to use the sidebar pet. The VS Code extension is packaged as a separate UI path; the MCP server remains the canonical state engine for Codex and Claude.

Build the VSIX locally from a clone:

```bash
./scripts/package-vscode.sh
```

On Windows from a clone:

```powershell
cd vscode-ext
npm ci
npm run package
code --install-extension .\chibi-mcp-*.vsix --force
```

## Local Verification

From a clone:

```bash
make check
```

This runs the Python server checks, Claude/Codex plugin validation, desktop lint, Rust checks, Tauri backend checks, VS Code package build, issue form YAML validation, and workflow sanity checks.

GitHub Actions also verifies:

- Python server on Linux, macOS, and Windows
- Windows PowerShell installer syntax
- desktop build smoke tests on Linux, macOS, and Windows
- VS Code `.vsix` packaging
- Rust/Tauri formatting and linting

`make check` verifies source/package correctness. If local GUI dependencies are missing, it reports a skip instead of treating the repository as broken.

To enforce local desktop runtime readiness:

```bash
make runtime-check
```

In a headless SSH/CI session, use a virtual display:

```bash
xvfb-run -a make runtime-check
```

For a stricter public-beta gate before sharing a release tag:

```bash
xvfb-run -a make public-beta-check
```

This runs strict source/runtime verification and a public-surface checklist for
README signals, rights docs, issue forms, plugin metadata, generated launch
images, and hidden legacy brand-name leaks.

For maintainer release-tag readiness after pushing `main`:

```bash
make release-check TAG=v1.4.35
```

See [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md).

On Ubuntu/Debian, Tauri requires system development packages before `make runtime-check` can pass:

```bash
sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential curl wget file pkg-config libdbus-1-dev libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

For the Python floating window on Ubuntu/Debian system Python:

```bash
sudo apt-get install -y python3-tk
```

For pyenv Python, install `tk-dev` first, then rebuild the Python version used by `pipx`/the venv.

## Maintainer Release Checklist

1. Update versions in `server/pyproject.toml`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and `vscode-ext/package.json`.
2. Push `main`, then run:

```bash
make release-check TAG=v1.4.35
```

3. Push a tag:

```bash
git tag v1.4.35
git push origin v1.4.35
```

4. GitHub Actions runs Python checks on Linux, macOS, and Windows; packages the VS Code `.vsix`; and builds desktop artifacts on Linux, macOS, and Windows.
5. GitHub Actions publishes the GitHub Release and attaches the wheel, source archive, `.vsix`, per-OS desktop artifacts, and `SHA256SUMS.txt`.

PyPI publishing is optional. Set the repository variable `PUBLISH_PYPI=true` only after PyPI Trusted Publishing is configured for this repo.
