# Contributing

Thanks for helping make `chibi-mcp` easier to install, safer to run, and more fun to use.

## Good First Contributions

- Fix install docs for Claude Code, Codex, VS Code, Linux, macOS, or Windows.
- Improve `chibi-mcp --check` diagnostics.
- Add tests for MCP tools, catalog handling, or window state.
- Polish starter character metadata.
- Propose a character pack through the issue template.
- Validate a sample creator/team pack with `chibi-pack validate`.
- Add screenshots, demo GIFs, or share-card examples.

## Local Setup

```bash
pipx install "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
chibi-mcp --check
```

From a clone:

```bash
make check
```

This runs Python lint/tests, build checks, Claude/Codex plugin validation, desktop lint, VS Code packaging, and workflow sanity checks.

## Pull Requests

- Keep changes scoped.
- Preserve the no-telemetry default.
- Do not add paid gates to the four base modes.
- Update docs when install, release, or user-facing behavior changes.
- Add or update tests for behavior changes.
- Run `make check` before opening a PR when possible.

## Character Packs

Character pack proposals should include:

- transparent PNG assets
- `meta.json` entry
- top-level `license` and `source_rights` fields in `meta.json`
- clear source/ownership statement
- source/provenance files if maintainers request them during review
- no copyrighted third-party character, logo, or brand use without permission
- no misleading claim that a fork, pack, or variant is an official project release
- no NSFW content

Use [docs/CREATOR_PACKS.md](docs/CREATOR_PACKS.md) and [ASSET_RIGHTS.md](ASSET_RIGHTS.md) as the submission guide. Runnable examples live under `examples/packs/`, and validation is:

```bash
chibi-pack validate --submission examples/packs/spring-hwajeon
chibi-pack validate --submission examples/packs/team-sprint
```
