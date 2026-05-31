# Security Policy

## Supported Versions

Security fixes target the latest `main` branch and the latest GitHub Release.

## Security Model

`chibi-mcp` is designed as a local-first MCP pet:

- no telemetry
- localhost WebSocket by default
- local state only
- no cloud account requirement
- no active paid entitlement gate in the open-source core

MCP servers and plugins can execute local code, so install only from a repository you trust and review the install scripts before running one-line installers.

Useful local checks:

```bash
chibi-audit
chibi-pack validate ./my-pack
```

Character and option pack images are expected to stay inside the pack directory; explicit image paths that escape the pack are rejected by `chibi-pack validate`.

## Verifying release authenticity

Release artifacts (the Python wheel/sdist and the VS Code `.vsix`) carry [SLSA build provenance](https://slsa.dev/) published as GitHub Artifact Attestations (signed via Sigstore). After downloading a release asset you can confirm it was built by this repository's CI — not a copycat or tampered re-upload — with the GitHub CLI:

```bash
gh attestation verify chibi_mcp-<version>-py3-none-any.whl --repo soccz/chibi-mcp
gh attestation verify chibi-mcp-<version>.vsix --repo soccz/chibi-mcp
```

`SHA256SUMS.txt` proves a download was not corrupted in transit (integrity); the attestation additionally proves *where it came from* (authenticity / provenance). Use both.

## Reporting a Vulnerability

Use GitHub private vulnerability reporting if it is enabled for this repository.

If private reporting is not enabled, open a minimal public issue titled `Security contact request` without exploit details. A maintainer should then provide a private contact path.

Please do not post working exploits, secrets, or sensitive local paths in public issues.
