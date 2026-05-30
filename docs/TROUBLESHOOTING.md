# Troubleshooting

Use this when the GitHub installer completed but Claude Code, Codex, VS Code, or the floating pet does not behave as expected.

## Quick Diagnostic

Run:

```bash
chibi-mcp --check
chibi-mcp --doctor
```

or:

```bash
chibi-check
```

Useful fields:

- `ok`: package and assets loaded correctly.
- `tkinter`: the Python floating window can open.
- `asset_dir`: packaged PNG assets are available.
- `catalog_count` / `option_count`: characters and free option layers are installed.

If you open an issue, paste this output after removing private paths.

## Command Not Found

If `chibi-mcp`, `chibi-check`, or `chibi-say` is not found after install:

```bash
pipx ensurepath
```

Restart the terminal, then retry:

```bash
chibi-mcp --check
```

On Windows PowerShell:

```powershell
py -m pipx ensurepath
chibi-mcp --check
```

## Floating Window Does Not Open

The MCP server can work in a terminal or headless session, but the pet window needs a desktop session and Python `tkinter`.

Linux display check:

```bash
echo "$DISPLAY"
echo "$WAYLAND_DISPLAY"
chibi-mcp --check
```

Ubuntu/Debian system Python:

```bash
sudo apt-get install -y python3-tk
```

macOS Homebrew Python:

```bash
python3 --version
python3 -m tkinter
```

If this fails with `ModuleNotFoundError: No module named '_tkinter'`, install the Tk package that matches your Homebrew Python minor version. For Python 3.14:

```bash
brew install python-tk@3.14
pipx uninstall chibi-mcp || true
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
chibi-mcp --check
```

If Homebrew changes the available formula name, run `brew search python-tk` and install the matching `python-tk@X.Y` package.

If macOS shows a Python crash report mentioning `_objc.cpython-314-darwin.so`,
upgrade to the latest installer. chibi no longer enters the PyObjC
transparency path and uses a stable Tk light-panel window on macOS.

The Claude/Codex bash installers attempt Tk repair automatically when `chibi-mcp --check` reports `tkinter: false`, then reinstall from the GitHub server subdirectory and check again. Supported automatic repair paths:

- macOS Homebrew: `python-tk@X.Y`
- Ubuntu/Debian: `python3-tk`
- Fedora/RHEL: `python3-tkinter`
- Arch: `tk`
- openSUSE: `python3-tk`
- Alpine: `py3-tkinter`

To disable automatic Tk repair:

```bash
CHIBI_SKIP_TK_REPAIR=1 bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.sh)
```

On Windows, the PowerShell installers try to install `pipx` automatically. If Python itself is missing and `winget` is available, they try to install Python first. If `tkinter` is still false after install, install or repair Python with Tcl/Tk support, then run:

```powershell
pipx uninstall chibi-mcp
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
chibi-mcp --check
```

pyenv Python:

1. Install OS Tk development packages such as `tk-dev`.
2. Rebuild the Python version used by `pipx`.
3. Reinstall `chibi-mcp` from the GitHub server subdirectory.

In SSH/headless CI, `open_pet_window` returns a diagnostic instead of crashing.

## Claude Code Does Not See Chibi

Verify the server command exists:

```bash
chibi-mcp --check
chibi-mcp --doctor
```

Then test the actual floating window outside Claude/Codex:

```bash
chibi-mcp --open
```

If this returns `opened: false`, use the printed `reason`, `next_step`, and
`log_path` values. `chibi-mcp --open` also starts a local `--ws-only` helper
when needed, so a direct standalone test should still allow toolbar actions.
The detailed logs are usually:

```bash
cat ~/.chibi-mcp/window.log
cat ~/.chibi-mcp/ws.log
```

If you set `CHIBI_RUNTIME_DIR`, use that directory instead of
`~/.chibi-mcp`. `chibi-mcp --doctor` prints the exact `runtime_dir`,
`pid_file`, and `log_path` values.

Register it manually:

```bash
claude mcp add chibi -- chibi-mcp
```

If using the Claude plugin path, the plugin gives `/chibi-mcp:chibi` commands, but the Python server still has to be installed so the `chibi-mcp` command is available.

## Claude Says `Please run /login` Or `401 Invalid Authentication`

This is a Claude Code authentication failure, not a chibi runtime failure.
Claude stops before it loads the `/chibi-mcp:chibi` command or calls the local
MCP server.

In Claude Code, run:

```text
/login
```

Then fully retry:

```text
/chibi-mcp:chibi
```

To prove the local chibi install works without Claude authentication, run these
from a normal terminal:

```bash
chibi-mcp --check
chibi-mcp --open
chibi-mcp --doctor
```

`chibi-mcp --doctor` reports Claude auth and MCP registration separately, so a
Claude 401 does not get mistaken for a local chibi failure. If `ok` is true but
`ready` is false, use the printed `next_steps`; the local server is installed,
but at least one client login, MCP registration, or VS Code extension check is
not ready.

If `/chibi-mcp:chibi` prints `Unknown command: /chibi`, Claude is still using
an old plugin command. Rerun the installer, then restart Claude Code:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.sh)
```

On Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.ps1 | iex"
```

## Rhythm Or Gacha Tickets Do Not Move

Claude Code must load the refreshed plugin hooks. After installing, fully quit
and reopen Claude Code, then run:

```text
/chibi-mcp:chibi
```

The hook records each `PostToolUse` event through `chibi-say --tool-call`.
Bubbles are intentionally throttled, but the rhythm counter should still move.
Tickets refill as follows:

- first pull of the local calendar day is free;
- +1 ticket per 100 captured tool calls;
- +1 ticket per 10 rhythm slices.

If the floating window shows `연결중` or `오프`, first run:

```bash
chibi-mcp --open
```

That command starts the local WebSocket helper automatically. If the status
stays offline, inspect `~/.chibi-mcp/ws.log`; the usual causes are another
process already using `127.0.0.1:9876`, a custom `CHIBI_WS_PORT`, or a failed
Python environment.

With `CHIBI_RUNTIME_DIR` set, inspect `$CHIBI_RUNTIME_DIR/ws.log` instead.

## Codex Does Not See Chibi

Verify the server command exists:

```bash
chibi-mcp --check
chibi-mcp --doctor
```

Register it manually:

```bash
codex mcp add chibi -- chibi-mcp
```

Optional local plugin marketplace registration from a clone:

```bash
codex plugin marketplace add .
```

If `clients.codex.auth.status` is `login_required`, run:

```bash
codex login
```

If `clients.codex.mcp.status` is `not_registered`, refresh the MCP entry:

```bash
codex mcp remove chibi || true
codex mcp add chibi -- chibi-mcp
```

## VS Code Installer Fails

The VS Code installer needs the `code` command on PATH.

In VS Code, run:

```text
Shell Command: Install 'code' command in PATH
```

Then retry the installer.

Manual install from a downloaded `.vsix`:

```bash
code --install-extension chibi-mcp-*.vsix --force
code --list-extensions
```

`chibi-mcp --doctor` reports whether `soccz.chibi-mcp` is visible to the `code`
CLI. If `code --list-extensions` cannot connect to VS Code, open VS Code once
and reinstall the `code` shell command.

Windows PowerShell from a clone:

```powershell
cd vscode-ext
npm ci
npm run package
code --install-extension .\chibi-mcp-*.vsix --force
```

## Windows PowerShell Installer Is Blocked

Use the documented one-command installer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.ps1 | iex"
```

Swap `install-claude.ps1` for `install-codex.ps1` or `install-vscode.ps1` as needed.

If your organization blocks `ExecutionPolicy Bypass`, clone the repo and inspect the script locally before running it.

## Release Download Verification

Tagged GitHub Releases attach `SHA256SUMS.txt` next to the wheel, source archive, `.vsix`, and desktop artifacts.

Linux/macOS:

```bash
sha256sum -c SHA256SUMS.txt
```

Windows PowerShell example for one file:

```powershell
Get-FileHash .\chibi-mcp-*.vsix -Algorithm SHA256
```

Compare the hash with `SHA256SUMS.txt`.

## What To Include In An Issue

Use the install problem or bug report template and include:

- OS and version.
- Install path: Claude Code, Codex, VS Code, or manual `pipx`.
- Exact command used.
- Output from `chibi-mcp --check`.
- Whether this is a desktop session, SSH, WSL, dev container, or CI.

Do not paste tokens, private repository paths, API keys, or full home-directory names.
