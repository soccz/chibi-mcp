# chibi-mcp-desktop

chibi — local desktop character. Cross-platform Tauri app that connects to the chibi-mcp server (`ws://127.0.0.1:9876`) and renders the character on your desktop.

## Quick run (local development)

Pre-req: Rust + Node.js + Linux deps.

Ubuntu/Debian:

```bash
sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential curl wget file pkg-config libdbus-1-dev libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

```bash
cd desktop
npm install
npm run tauri dev
```

For browser-only preview (no Tauri, no apt install):

```bash
python3 -m http.server 8767 --bind 127.0.0.1 --directory src
# then open http://localhost:8767/preview-pet.html
```

## Architecture

- `src/` — frontend (HTML/CSS/JS). Loaded by Tauri as static assets.
- `src/main.js` — character runtime (state machine, WebSocket client, animations).
- `src/characters/<id>/base.svg` — character art. Swap files here to change look.
- `src-tauri/` — Rust shell. Configures the pet window (transparent, frameless, always-on-top).

## Character slot

The runtime loads `characters/<CHARACTER_ID>/base.svg` and treats specific element ids as anchors:

- `#body` — main rect; for length growth (future)
- `#eyes` — group replaced per mood by main.js
- `#mouth`, `#mouth-inner` — path d attributes set per mood
- `#syrup-layer` — group where new drip elements are appended
- `#knife` — hidden by default; animates in on slice event

To add a new character (e.g., a future illustrator commission):
1. Make `characters/<your-id>/base.svg` with the ids above
2. Add `characters/<your-id>/meta.json`
3. Set `CHARACTER_ID = "<your-id>"` in `main.js` (later: settings UI)

## Window

- Size: 720×220 (matches base.svg viewBox 0 0 700 220)
- Transparent background (tauri.conf.json)
- Always-on-top, frameless, skip taskbar
- WebSocket connects to `ws://127.0.0.1:9876`. CSP whitelists this.

## Builds

CI builds for all three OSes on push (see `.github/workflows/build.yml`).
Tagged releases create draft GitHub Releases with `.dmg` / `.deb` / `.exe` / `.AppImage` / `.msi`.

## License

MIT
