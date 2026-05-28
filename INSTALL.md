# Install from GitHub

This repo supports three user-facing paths from the same GitHub source:

- Claude Code: MCP server plus Claude plugin commands.
- Codex: MCP server plus optional Codex plugin marketplace metadata.
- VS Code: downloadable `.vsix` from GitHub Releases.

## Prerequisites

- Python 3.12+
- `pipx` on your PATH
- A real desktop session if you want the floating pet window
- Python `tkinter` support for the floating window (`chibi-mcp --check` reports this). On Ubuntu/Debian system Python, install `python3-tk`; for pyenv Python, install `tk-dev` and rebuild Python.

## One-command installs

Claude Code:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-claude.sh)
```

Codex:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/soccz/chibi-mcp/main/scripts/install-codex.sh)
```

Both scripts install or upgrade the `chibi-mcp` server with `pipx`, run `chibi-mcp --check`, then register the MCP server with the selected client.

## Manual server install

Install the MCP server directly from GitHub:

```bash
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
```

For upgrades from GitHub:

```bash
pipx upgrade chibi-mcp
```

Verify the install:

```bash
chibi-mcp --check
```

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
내 치비 보여줘
치비 뽑기 한 번
치비 보관함 열어
```

## Claude Code

Direct MCP registration:

```bash
claude mcp add chibi -- chibi-mcp
```

Plugin registration inside Claude Code:

```text
/plugin marketplace add soccz/chibi-mcp
/plugin install chibi@chibi-mcp
```

The plugin gives Claude the `/chibi` command and the `chibi` skill prompt. The MCP server must still be installed with `pipx` so the `chibi-mcp` command is available.

## VS Code

Download the latest `.vsix` from GitHub Releases, then run:

```bash
code --install-extension chibi-mcp-*.vsix
```

Open the `tteoki` activity bar view to use the sidebar pet. The VS Code extension is packaged as a separate UI path; the MCP server remains the canonical state engine for Codex and Claude.

Build the VSIX locally from a clone:

```bash
./scripts/package-vscode.sh
```

## Local Verification

From a clone:

```bash
make check
```

This runs the Python server checks, Claude/Codex plugin validation, desktop lint, Rust checks, Tauri backend checks, VS Code package build, issue form YAML validation, and workflow sanity checks.

`make check` verifies source/package correctness. If local GUI dependencies are missing, it reports a skip instead of treating the repository as broken.

To enforce local desktop runtime readiness:

```bash
make runtime-check
```

In a headless SSH/CI session, use a virtual display:

```bash
xvfb-run -a make runtime-check
```

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
2. Push a tag:

```bash
git tag v1.1.1
git push origin v1.1.1
```

3. GitHub Actions builds Python checks, Python wheel/sdist, desktop artifacts, and the VS Code `.vsix`.
4. GitHub Actions publishes the GitHub Release and attaches the build artifacts.

PyPI publishing is optional. Set the repository variable `PUBLISH_PYPI=true` only after PyPI Trusted Publishing is configured for this repo.
