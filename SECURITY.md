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

Character pack images are expected to stay inside the pack directory; explicit image paths that escape the pack are rejected by `chibi-pack validate`.

## Reporting a Vulnerability

Use GitHub private vulnerability reporting if it is enabled for this repository.

If private reporting is not enabled, open a minimal public issue titled `Security contact request` without exploit details. A maintainer should then provide a private contact path.

Please do not post working exploits, secrets, or sensitive local paths in public issues.
