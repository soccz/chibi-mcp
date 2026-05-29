# Publishing the VS Code extension

The extension at `vscode-ext/` ships as a `.vsix` attached to every tagged GitHub Release. Marketplace publication is a separate, manual step.

## What CI already does

On every tag push, `.github/workflows/build.yml` runs `scripts/package-vscode.sh` to produce `chibi-mcp-<version>.vsix` and attaches it to the GitHub Release. Users can install with:

```bash
code --install-extension chibi-mcp-<version>.vsix
```

This path is sufficient for distribution — no Marketplace listing required.

## Publishing to the VS Code Marketplace

Only do this when you want public discovery on `marketplace.visualstudio.com`.

### One-time setup

1. Create a [Microsoft Personal Access Token (PAT)](https://dev.azure.com/) scoped to **Marketplace > Manage**.
2. Create a [Marketplace publisher](https://marketplace.visualstudio.com/manage) named `soccz` (matches `publisher` in `vscode-ext/package.json`).
3. Locally:
   ```bash
   npm install -g @vscode/vsce
   vsce login soccz       # paste PAT
   ```

### Each release

From `vscode-ext/`:

```bash
npm install
npm run compile
vsce publish
```

`vsce publish` reads `package.json` `version` and uploads the built extension. To bump version inline:

```bash
vsce publish patch       # 0.5.0 -> 0.5.1
vsce publish minor       # 0.5.0 -> 0.6.0
vsce publish major       # 0.5.0 -> 1.0.0
```

The first publish may take a few minutes to appear in the Marketplace search index.

### Open VSX (Cursor / VSCodium / Theia)

Cursor and VSCodium users pull from [open-vsx.org](https://open-vsx.org/), not the Microsoft Marketplace. Mirror with:

```bash
npx ovsx publish chibi-mcp-<version>.vsix -p $OVSX_PAT
```

(`OVSX_PAT` from open-vsx.org publisher settings.)

## Verification before publishing

```bash
cd vscode-ext
npm run lint           # tsc --noEmit
npm run compile        # tsc -p ./
vsce package           # produces .vsix locally without publishing
code --install-extension chibi-mcp-*.vsix    # smoke-test
```

## Things to bump together

- `vscode-ext/package.json` `version`
- `vscode-ext/package-lock.json` (automatic via `npm install`)
- The same release commit in the repo root, so the `.vsix` lands in the matching GitHub Release.
