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
v1.4.6
```

## Preflight

Run this after committing and pushing `main`, before creating the tag:

```bash
make release-check TAG=v1.4.6
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
./scripts/release_preflight.sh v1.4.6 --allow-dirty --skip-public-beta
```

## Publish

After preflight passes:

```bash
git tag v1.4.6
git push origin v1.4.6
```

GitHub Actions will build the wheel, source archive, VS Code `.vsix`, desktop
artifacts, and `SHA256SUMS.txt`, then create the GitHub Release.

## After Publish

Verify:

- GitHub Actions for the tag is green.
- The release has `SHA256SUMS.txt`.
- The release has the `.vsix`.
- The release has Python wheel and source archive.
- Desktop artifacts are attached for the expected operating systems.
- README install commands still point to GitHub source/release paths.
- No paid gates or telemetry were introduced.

Manual launch assets still recommended before broad public launch:

- `docs/demo.gif`
- `docs/screenshots/vscode-sidebar.png`
- `docs/screenshots/claude-code.png`
- `docs/screenshots/codex-terminal.png`
