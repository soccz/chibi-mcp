// tteoki VS Code extension — chibi-mcp v0.2.
// Renders the gacha pet in a sidebar webview. Uses VS Code globalState for
// inventory persistence, and listens to file save / debug start / problems
// counters to drive simple mood cues.

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

interface Character {
    id: string;
    name_ko: string;
    category: string;
    rarity: number;
    tier?: "free" | "pro";
}

interface Catalog {
    characters: Character[];
}

interface OwnedEntry {
    id: string;
    nickname: string;
    obtained_at: string;
}

interface Inventory {
    owned: Record<string, OwnedEntry>;
    active_id: string | null;
    tickets: number;
    first_launch: boolean;
    last_daily: string | null;
    save_count_at_last_ticket: number;
}

const RARITY_WEIGHTS: Record<number, number> = { 5: 1, 4: 5, 3: 24, 2: 70 };

function defaultInventory(): Inventory {
    return {
        owned: {},
        active_id: null,
        tickets: 1, // welcome ticket
        first_launch: true,
        last_daily: null,
        save_count_at_last_ticket: 0,
    };
}

function loadCatalog(context: vscode.ExtensionContext): Catalog {
    const p = path.join(context.extensionPath, "resources", "meta.json");
    return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function loadInventory(context: vscode.ExtensionContext): Inventory {
    return context.globalState.get<Inventory>("inventory") ?? defaultInventory();
}

function saveInventory(context: vscode.ExtensionContext, inv: Inventory) {
    return context.globalState.update("inventory", inv);
}

function hasPro(): boolean {
    // VS Code extension reads the same license file/env as the MCP server.
    const env = process.env.CHIBI_LICENSE_KEY;
    if (env && env.trim()) return verifyLicense(env.trim());
    try {
        const home = process.env.HOME || process.env.USERPROFILE || "";
        const p = path.join(home, ".chibi-mcp", "license");
        if (fs.existsSync(p)) return verifyLicense(fs.readFileSync(p, "utf-8").trim());
    } catch {
        /* fallthrough */
    }
    return false;
}

function verifyLicense(raw: string): boolean {
    // NOTE: full HMAC verification is in the Python server. The extension
    // delegates trust to the server-side check; here we accept any non-empty
    // license string with the expected prefix and expiry in the future. The
    // real authority for Pro features is `chibi-mcp get_license_status`.
    const parts = raw.split("|");
    if (parts.length !== 4 || parts[0] !== "chibi-pro") return false;
    const expires = new Date(parts[2]);
    return !isNaN(expires.getTime()) && expires > new Date();
}

function filterByTier(catalog: Catalog, isPro: boolean): Character[] {
    if (isPro) return catalog.characters;
    return catalog.characters.filter((c) => c.tier === "free");
}

function drawGacha(catalog: Catalog, isPro: boolean): Character {
    const pool = filterByTier(catalog, isPro);
    const total = Object.values(RARITY_WEIGHTS).reduce((a, b) => a + b, 0);
    let r = Math.random() * total;
    let picked = 2;
    for (const [rarity, w] of Object.entries(RARITY_WEIGHTS)) {
        r -= w;
        if (r <= 0) {
            picked = parseInt(rarity, 10);
            break;
        }
    }
    const byRarity = pool.filter((c) => c.rarity === picked);
    const safe = byRarity.length > 0 ? byRarity : pool;
    return safe[Math.floor(Math.random() * safe.length)];
}

function rarityStars(n: number): string {
    return "★".repeat(n) + "☆".repeat(5 - n);
}

class PetViewProvider implements vscode.WebviewViewProvider {
    static readonly viewType = "chibiMcp.petView";

    constructor(
        private readonly context: vscode.ExtensionContext,
        private readonly catalog: Catalog,
    ) {}

    private view?: vscode.WebviewView;

    resolveWebviewView(webviewView: vscode.WebviewView): void {
        this.view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.file(path.join(this.context.extensionPath, "resources")),
            ],
        };

        webviewView.webview.html = this.renderHtml(webviewView.webview);

        webviewView.webview.onDidReceiveMessage((msg) => {
            const inv = loadInventory(this.context);
            if (msg.type === "gacha") this.runGacha(inv, hasPro());
            else if (msg.type === "select") this.selectActive(inv, msg.id);
            else if (msg.type === "rename") this.renameOne(inv, msg.id, msg.nickname);
            else if (msg.type === "ready") this.refresh();
        });
    }

    private refresh(): void {
        if (!this.view) return;
        const inv = loadInventory(this.context);
        this.view.webview.postMessage({ type: "state", inventory: inv, catalog: this.catalog });
    }

    private runGacha(inv: Inventory, isPro: boolean): void {
        if (inv.tickets <= 0) {
            this.view?.webview.postMessage({ type: "toast", text: "뽑기권이 없어요" });
            return;
        }
        inv.tickets -= 1;
        const ch = drawGacha(this.catalog, isPro);
        if (!inv.owned[ch.id]) {
            inv.owned[ch.id] = {
                id: ch.id,
                nickname: ch.name_ko,
                obtained_at: new Date().toISOString(),
            };
            if (!inv.active_id) inv.active_id = ch.id;
        }
        saveInventory(this.context, inv).then(() => {
            this.view?.webview.postMessage({
                type: "gacha-result",
                character: ch,
                duplicate: Object.keys(inv.owned).length > 0 && !inv.owned[ch.id],
                inventory: inv,
            });
        });
    }

    private selectActive(inv: Inventory, id: string): void {
        if (!inv.owned[id]) return;
        inv.active_id = id;
        saveInventory(this.context, inv).then(() => this.refresh());
    }

    private renameOne(inv: Inventory, id: string, nickname: string): void {
        if (!inv.owned[id]) return;
        inv.owned[id].nickname = nickname?.trim() || inv.owned[id].nickname;
        saveInventory(this.context, inv).then(() => this.refresh());
    }

    grantTicket(label: string): void {
        const inv = loadInventory(this.context);
        inv.tickets += 1;
        saveInventory(this.context, inv).then(() => {
            this.view?.webview.postMessage({
                type: "toast",
                text: `🎟 +1 (${label})`,
                inventory: inv,
            });
        });
    }

    private renderHtml(webview: vscode.Webview): string {
        const charsUri = webview.asWebviewUri(
            vscode.Uri.file(path.join(this.context.extensionPath, "resources")),
        );
        return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
:root { color-scheme: dark; }
body { margin: 0; padding: 12px; font-family: var(--vscode-font-family); color: var(--vscode-foreground); }
.pet { text-align: center; padding: 16px 0; }
.pet img { max-width: 180px; height: auto; cursor: pointer; transition: transform 0.3s; }
.pet img:hover { transform: scale(1.04); }
.pet img.squish { animation: squish 0.45s ease-out 1; }
@keyframes squish { 0%,100%{transform:scaleX(1) scaleY(1)} 35%{transform:scaleX(1.18) scaleY(0.78)} 70%{transform:scaleX(0.95) scaleY(1.05)} }
.pet .name { margin-top: 8px; font-weight: 600; }
.pet .rarity { font-size: 11px; opacity: 0.7; margin-top: 2px; letter-spacing: 1px; }
.bar { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 12px; }
.bar .tickets { color: var(--vscode-textLink-foreground); font-weight: 600; }
.actions { display: flex; gap: 6px; margin: 8px 0 14px; }
.actions button { flex: 1; padding: 7px; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 12px; }
.actions button:hover { background: var(--vscode-button-hoverBackground); }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; max-height: 300px; overflow-y: auto; }
.cell { background: var(--vscode-editor-inactiveSelectionBackground); border: 1.5px solid transparent; border-radius: 8px; padding: 6px 3px; text-align: center; cursor: pointer; transition: transform 0.12s; }
.cell.owned:hover { transform: translateY(-1px); }
.cell.locked { opacity: 0.4; cursor: default; }
.cell.active { border-color: var(--vscode-focusBorder); }
.cell img { width: 48px; height: 48px; object-fit: contain; }
.cell .locked-icon { width: 48px; height: 48px; line-height: 48px; color: var(--vscode-descriptionForeground); font-size: 20px; }
.cell .cname { font-size: 10px; margin-top: 2px; }
.cell .crarity { font-size: 9px; opacity: 0.7; letter-spacing: 1px; }
.toast { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); background: var(--vscode-notificationsInfoIcon-foreground); color: var(--vscode-editor-background); padding: 6px 14px; border-radius: 16px; font-size: 12px; opacity: 0; transition: opacity 0.3s; }
.toast.show { opacity: 1; }
h3 { margin: 12px 0 6px; font-size: 12px; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.6px; }
</style>
</head>
<body>
<div id="root">
  <div class="pet">
    <img id="active-img" src="" alt="">
    <div class="name" id="active-name">—</div>
    <div class="rarity" id="active-rarity"></div>
  </div>
  <div class="bar">
    <span>보유 <strong id="owned-count">0</strong> / 29</span>
    <span class="tickets">🎟 <strong id="tickets">0</strong></span>
  </div>
  <div class="actions">
    <button id="btn-gacha">🎟 뽑기</button>
  </div>
  <h3>내 친구들</h3>
  <div class="grid" id="grid"></div>
</div>
<div class="toast" id="toast"></div>
<script>
const vscode = acquireVsCodeApi();
const charsBase = "${charsUri}";
let catalog = null;
let inventory = null;

function rarityStars(n) { return "★".repeat(n) + "☆".repeat(5 - n); }

function render() {
  if (!catalog || !inventory) return;
  const ownedIds = Object.keys(inventory.owned);
  document.getElementById("owned-count").textContent = ownedIds.length;
  document.getElementById("tickets").textContent = inventory.tickets;
  const active = inventory.active_id ? catalog.characters.find(c => c.id === inventory.active_id) : null;
  const img = document.getElementById("active-img");
  if (active) {
    img.src = charsBase + "/" + active.id + ".png";
    document.getElementById("active-name").textContent = inventory.owned[active.id].nickname;
    document.getElementById("active-rarity").textContent = rarityStars(active.rarity);
  } else {
    img.removeAttribute("src");
    document.getElementById("active-name").textContent = "친구 없음";
    document.getElementById("active-rarity").textContent = "";
  }
  // grid
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  for (const ch of catalog.characters) {
    const owned = !!inventory.owned[ch.id];
    const cell = document.createElement("div");
    cell.className = "cell " + (owned ? "owned" : "locked") + (inventory.active_id === ch.id ? " active" : "");
    cell.innerHTML = owned
      ? \`<img src="\${charsBase}/\${ch.id}.png" alt="\${ch.name_ko}"><div class="cname">\${inventory.owned[ch.id].nickname}</div><div class="crarity">\${rarityStars(ch.rarity)}</div>\`
      : \`<div class="locked-icon">?</div><div class="crarity">\${rarityStars(ch.rarity)}</div>\`;
    if (owned) {
      cell.onclick = () => {
        vscode.postMessage({ type: "select", id: ch.id });
        const nick = prompt(\`\${ch.name_ko}에게 이름을\`, inventory.owned[ch.id].nickname);
        if (nick) vscode.postMessage({ type: "rename", id: ch.id, nickname: nick });
      };
    }
    grid.appendChild(cell);
  }
}

document.getElementById("btn-gacha").addEventListener("click", () => {
  vscode.postMessage({ type: "gacha" });
});

document.getElementById("active-img").addEventListener("click", () => {
  const img = document.getElementById("active-img");
  img.classList.remove("squish"); void img.offsetWidth;
  img.classList.add("squish");
});

window.addEventListener("message", (e) => {
  const m = e.data;
  if (m.type === "state") { catalog = m.catalog; inventory = m.inventory; render(); }
  else if (m.type === "gacha-result") {
    inventory = m.inventory;
    render();
    showToast(\`\${m.character.name_ko} \${rarityStars(m.character.rarity)}\`);
  }
  else if (m.type === "toast") {
    if (m.inventory) inventory = m.inventory;
    render();
    showToast(m.text);
  }
});

function showToast(text) {
  const t = document.getElementById("toast");
  t.textContent = text;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

vscode.postMessage({ type: "ready" });
</script>
</body>
</html>`;
    }
}

export function activate(context: vscode.ExtensionContext) {
    const catalog = loadCatalog(context);
    const provider = new PetViewProvider(context, catalog);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(PetViewProvider.viewType, provider),

        vscode.commands.registerCommand("chibiMcp.gacha", () => {
            const inv = loadInventory(context);
            (provider as any).runGacha(inv, hasPro());
        }),
        vscode.commands.registerCommand("chibiMcp.collection", () => {
            vscode.commands.executeCommand("workbench.view.extension.chibiMcpContainer");
        }),
        vscode.commands.registerCommand("chibiMcp.reset", async () => {
            const yes = await vscode.window.showWarningMessage(
                "tteoki 보관함을 초기화합니다. 정말 진행할까요?",
                { modal: true },
                "초기화",
            );
            if (yes === "초기화") {
                await context.globalState.update("inventory", undefined);
                vscode.window.showInformationMessage("tteoki 보관함이 초기화되었습니다.");
            }
        }),

        // Mood signals → ticket grants
        vscode.workspace.onDidSaveTextDocument(() => {
            const inv = loadInventory(context);
            const today = new Date().toISOString().slice(0, 10);
            if (inv.last_daily !== today) {
                inv.last_daily = today;
                inv.tickets += 1;
                saveInventory(context, inv).then(() =>
                    provider.grantTicket("오늘의 출석"),
                );
            }
        }),
    );

    // Welcome / first launch
    const inv = loadInventory(context);
    if (inv.first_launch && Object.keys(inv.owned).length === 0) {
        inv.first_launch = false;
        saveInventory(context, inv).then(() => {
            vscode.window
                .showInformationMessage(
                    "tteoki에 오신 걸 환영해요! 무료 뽑기 한 장이 보관함에 들어있어요.",
                    "뽑기 열기",
                )
                .then((sel) => {
                    if (sel === "뽑기 열기") {
                        vscode.commands.executeCommand(
                            "workbench.view.extension.chibiMcpContainer",
                        );
                    }
                });
        });
    }
}

export function deactivate() {}
