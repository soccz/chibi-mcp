# Release Process

Use this when publishing a GitHub Release tag. This process keeps public beta
distribution free and does not enable paid packs, checkout, license keys,
Sponsors tiers, team pricing, or paid random pulls.

## Current Release Candidate

The server, Claude plugin, and Codex plugin versions are expected to match the
release tag. VS Code and desktop app versions are reported separately because
they are packaged as separate clients.

For the current package metadata, the next release tag is:

```bash
v1.4.19
```

## Preflight

Run this after committing and pushing `main`, before creating the tag:

```bash
make release-check TAG=v1.4.19
```

This checks:

- tag format and version match;
- server, Claude plugin, and Codex plugin version alignment;
- clean worktree;
- local `HEAD` equals upstream `origin/main`;
- the tag does not already exist locally;
- full public beta preflight.

For a quick version-only check while editing:

```bash
./scripts/release_preflight.sh v1.4.19 --allow-dirty --skip-public-beta
```

## Publish

After preflight passes:

```bash
git tag v1.4.19
git push origin v1.4.19
```

GitHub Actions will build the wheel, source archive, VS Code `.vsix`, desktop
artifacts, and `SHA256SUMS.txt`, then create the GitHub Release.

## Enabling PyPI publishing (one-time, optional)

The `chibi-mcp` PyPI project **already exists and is owned by the maintainer**
(published through `1.1.0` on 2026-05-28). It is currently **stale**: the repo
is at a newer version and the latest PyPI release still shows the old
food-themed description. Automated publishing via CI is **off by default**
(`vars.PUBLISH_PYPI` unset). The release CI ships a `pypi-publish` job using PyPI
**Trusted Publishing** (OIDC, no API token, PEP 740 attestations automatic).

> Publishing the current (clean-branding) version also **refreshes the public
> PyPI description**, replacing the stale food-themed text shown on the project
> page. The actual publish is an account action only the maintainer can perform.

To enable automated CI publishing:

1. **PyPI — add a Trusted Publisher to the existing `chibi-mcp` project**
   (pypi.org → *Your projects* → `chibi-mcp` → *Manage* → *Publishing* → *Add*).
   For a brand-new project name use *Add a pending publisher* instead. Values:
   - PyPI Project Name: `chibi-mcp`
   - Owner: `soccz`
   - Repository name: `chibi-mcp`
   - Workflow name: `build.yml`
   - Environment name: *(leave blank — the job uses no GitHub Environment)*
2. **GitHub — flip the variable**: repo *Settings → Secrets and variables →
   Actions → Variables → New repository variable*: `PUBLISH_PYPI` = `true`.
3. **Push a version tag** (`git tag v1.4.39 && git push origin v1.4.39`). The
   `pypi-publish` job builds `chibi-mcp` (sdist + wheel) and uploads it with
   build-provenance attestations attached automatically.

Verify after the first publish: `pipx install chibi-mcp` works, and the PyPI
project page shows the release with provenance. Adding `pipx install chibi-mcp`
to the README as a shorter install path is then an optional maintainer choice.

This is an additional public release channel; per SPEC.md it is a maintainer
decision, currently recorded as pending.

## After Publish

Verify:

- GitHub Actions for the tag is green.
- The release has `SHA256SUMS.txt`.
- The release has the `.vsix`.
- The release has Python wheel and source archive.
- Desktop artifacts are attached for the expected operating systems.
- README install commands still point to GitHub source/release paths.
- No paid gates or telemetry were introduced.

Generated launch assets included in public beta:

- `docs/demo.gif`
- `docs/screenshots/vscode-sidebar.png`
- `docs/screenshots/claude-code.png`
- `docs/screenshots/codex-terminal.png`

Before a larger external launch, replace at least one generated preview with a
real user-captured desktop screenshot.
