// main.js — chibi v0.2 pet runtime.
//
// 1. Loads the character catalog + user inventory.
// 2. On first launch, prompts the welcome / first-free-gacha flow.
// 3. Renders the active character (PNG) and pipes mood/say/slice events
//    from the MCP WebSocket server.
// 4. Wires right-click menu (gacha / collection / size / quit) and the
//    slangy interaction (click squish, drag stretch).

import {
    loadCatalog,
    loadInventory,
    saveInventory,
    ownsCharacter,
    ownedCount,
    addCharacter,
    renameCharacter,
    setActive,
    activeCharacter,
    consumeTicket,
    grantTicket,
    drawGacha,
    evaluateTicketGrants,
    rarityStars,
    rarityClass,
} from "./inventory.js";

const WS_URL = "ws://127.0.0.1:9876";
const RECONNECT_INITIAL_MS = 2000;
const RECONNECT_MAX_MS = 30000;
const RECONNECT_BACKOFF = 2.0;

let catalog = null;
let inventory = null;
let ws = null;
let reconnectScheduled = false;
let reconnectDelay = RECONNECT_INITIAL_MS;
let speechTimer = null;
let dripTimer = null;
let lastCounters = { calls_total: 0, slices_today: 0, slice_interval: 10 };

// ============== CHARACTER RENDER ==============

function renderActiveCharacter() {
    const ch = activeCharacter(inventory, catalog);
    const img = document.getElementById("active-char");
    if (!ch) {
        img.removeAttribute("src");
        img.style.visibility = "hidden";
        return;
    }
    img.src = `characters/${ch.id}.png`;
    img.alt = ch.name_ko;
    img.style.visibility = "visible";
}

function applyMood(mood) {
    const stage = document.getElementById("stage");
    stage.dataset.mood = mood || "calm";
    document.getElementById("hud-mood").textContent = mood || "calm";

    if (mood === "panting") setDripCadence(1.0);
    else if (mood === "drowsy" || mood === "lonely") setDripCadence(0);
    else setDripCadence(4.0);
}

function updateHud(state) {
    if (state.mood) document.getElementById("hud-mood").textContent = state.mood;
    const c = state.counters ?? {};
    lastCounters = { ...lastCounters, ...c };
    document.getElementById("hud-slices").textContent = `${c.slices_today ?? 0}도막`;
    document.getElementById("hud-calls").textContent =
        `${c.calls_since_slice ?? 0}/${c.slice_interval ?? "?"}`;
    document.getElementById("hud-tickets").textContent = `🎟 ${inventory.tickets}`;

    // Ticket grants based on counters
    const granted = evaluateTicketGrants(inventory, lastCounters);
    if (granted > 0) {
        document.getElementById("hud-tickets").textContent = `🎟 ${inventory.tickets} (+${granted})`;
        flashTicketGain(granted);
    }
}

function flashTicketGain(n) {
    speak(`🎟 +${n} 뽑기권 획득!`);
}

// ============== DRIP / SLICE / SPEECH ==============

function setDripCadence(seconds) {
    if (dripTimer) clearInterval(dripTimer);
    if (!seconds || seconds <= 0) return;
    dripTimer = setInterval(spawnDrip, seconds * 1000);
}

function spawnDrip() {
    const layer = document.getElementById("stage");
    if (!layer) return;
    const drop = document.createElement("div");
    drop.className = "syrup-drop";
    const img = document.getElementById("active-char");
    const rect = img.getBoundingClientRect();
    drop.style.left = `${rect.left + rect.width * (0.3 + Math.random() * 0.4)}px`;
    drop.style.top = `${rect.bottom - 20}px`;
    layer.appendChild(drop);
    setTimeout(() => drop.remove(), 1800);
}

function dropSlicePiece() {
    const board = document.getElementById("board");
    const piece = document.createElement("div");
    piece.className = "slice-piece";
    const x = 30 + Math.random() * (window.innerWidth - 90);
    piece.style.left = `${x}px`;
    board.appendChild(piece);
    setTimeout(() => piece.remove(), 5500);
}

function speak(text) {
    if (!text) return;
    const s = document.getElementById("speech");
    s.textContent = text;
    s.classList.remove("hidden");
    requestAnimationFrame(() => s.classList.add("show"));
    if (speechTimer) clearTimeout(speechTimer);
    speechTimer = setTimeout(() => {
        s.classList.remove("show");
        setTimeout(() => s.classList.add("hidden"), 250);
    }, 3500);
}

// ============== SLANGY INTERACTION ==============

function setupSlangy() {
    const img = document.getElementById("active-char");
    img.addEventListener("click", (e) => {
        e.stopPropagation();
        img.classList.remove("squish");
        void img.getBoundingClientRect();
        img.classList.add("squish");
        setTimeout(() => img.classList.remove("squish"), 450);
    });
    img.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        img.classList.remove("bounce");
        void img.getBoundingClientRect();
        img.classList.add("bounce");
        setTimeout(() => img.classList.remove("bounce"), 550);
    });
}

// ============== WEBSOCKET ==============

function connect() {
    reconnectScheduled = false;
    try {
        ws = new WebSocket(WS_URL);
    } catch {
        scheduleReconnect();
        return;
    }
    ws.onopen = () => {
        setConnected(true);
        reconnectDelay = RECONNECT_INITIAL_MS;
    };
    ws.onclose = () => {
        setConnected(false);
        scheduleReconnect();
    };
    ws.onerror = () => {};
    ws.onmessage = (evt) => {
        try {
            handleMessage(JSON.parse(evt.data));
        } catch (e) {
            console.warn("bad ws message", e);
        }
    };
}

function scheduleReconnect() {
    if (reconnectScheduled) return;
    reconnectScheduled = true;
    const delay = Math.min(reconnectDelay, RECONNECT_MAX_MS);
    setTimeout(connect, delay);
    reconnectDelay = Math.min(reconnectDelay * RECONNECT_BACKOFF, RECONNECT_MAX_MS);
}

function setConnected(ok) {
    document.getElementById("stage").dataset.connected = ok ? "true" : "false";
    if (!ok) document.getElementById("hud-mood").textContent = "offline";
}

function handleMessage(msg) {
    if (msg.type === "state") {
        applyMood(msg.payload?.mood);
        updateHud(msg.payload ?? {});
    } else if (msg.type === "say") {
        speak(msg.text ?? "");
    } else if (msg.type === "slice") {
        dropSlicePiece();
    }
}

// ============== CONTEXT MENU ==============

const SIZES = {
    "size-small":  { w: 240, h: 240 },
    "size-normal": { w: 340, h: 340 },
    "size-large":  { w: 500, h: 500 },
};

function setupContextMenu() {
    const menu = document.getElementById("ctx-menu");
    document.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        menu.classList.remove("hidden");
        menu.style.left = `${Math.min(e.clientX, window.innerWidth - 180)}px`;
        menu.style.top = `${Math.min(e.clientY, window.innerHeight - 240)}px`;
    });
    document.addEventListener("click", () => menu.classList.add("hidden"));
    menu.addEventListener("click", async (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        const action = btn.dataset.action;
        menu.classList.add("hidden");
        if (action === "quit") {
            await tauriQuit();
        } else if (action === "gacha") {
            tryGacha();
        } else if (action === "collection") {
            openCollection();
        } else if (SIZES[action]) {
            await tauriResize(SIZES[action]);
        }
    });
}

async function tauriQuit() {
    try {
        const w = window.__TAURI__.window;
        await w.getCurrentWindow().close();
    } catch {
        window.close();
    }
}

async function tauriResize({ w, h }) {
    try {
        const t = window.__TAURI__.window;
        await t.getCurrentWindow().setSize(new t.LogicalSize(w, h));
    } catch {
        window.resizeTo(w, h);
    }
}

// ============== WELCOME / GACHA ==============

function openWelcome() {
    showModal("welcome-modal");
    document.getElementById("welcome-draw").onclick = () => {
        hideModal("welcome-modal");
        // ensure a free ticket exists
        if (inventory.tickets < 1) grantTicket(inventory, 1);
        runGacha({ firstFree: true });
    };
}

function tryGacha() {
    if (inventory.tickets <= 0) {
        speak("뽑기권이 없어요");
        return;
    }
    consumeTicket(inventory);
    runGacha({ firstFree: false });
}

function runGacha({ firstFree: _firstFree }) {
    const ch = drawGacha(catalog);
    const dup = ownsCharacter(inventory, ch.id);
    if (!dup) addCharacter(inventory, ch);
    else saveInventory(inventory); // re-saved in addCharacter, but harmless

    document.getElementById("hud-tickets").textContent = `🎟 ${inventory.tickets}`;

    // Show modal with reveal
    showModal("gacha-modal");
    const reveal = document.getElementById("gacha-reveal");
    const rarity = document.getElementById("gacha-rarity");
    const name = document.getElementById("gacha-name");
    reveal.src = `characters/${ch.id}.png`;
    reveal.className = `reveal-img ${rarityClass(ch.rarity)}`;
    rarity.textContent = rarityStars(ch.rarity);
    rarity.className = `gacha-rarity ${rarityClass(ch.rarity)}`;
    name.textContent = dup ? `${ch.name_ko} (중복)` : ch.name_ko;

    document.getElementById("gacha-rename").onclick = () => {
        hideModal("gacha-modal");
        openRename(ch.id, ch.name_ko, () => {
            setActive(inventory, ch.id);
            renderActiveCharacter();
        });
    };
    document.getElementById("gacha-use").onclick = () => {
        setActive(inventory, ch.id);
        renderActiveCharacter();
        hideModal("gacha-modal");
    };
    document.getElementById("gacha-keep").onclick = () => {
        hideModal("gacha-modal");
    };
}

function openRename(id, typeName, onSave) {
    showModal("rename-modal");
    const input = document.getElementById("rename-input");
    const current = inventory.owned[id]?.nickname ?? typeName;
    input.value = current;
    input.focus();
    input.select();
    document.getElementById("rename-subtitle").textContent = `${typeName}에게 별명을 지어주세요`;
    document.getElementById("rename-save").onclick = () => {
        renameCharacter(inventory, id, input.value);
        hideModal("rename-modal");
        onSave?.();
    };
    document.getElementById("rename-cancel").onclick = () => {
        hideModal("rename-modal");
        onSave?.();
    };
}

// ============== COLLECTION ==============

function openCollection() {
    const grid = document.getElementById("collection-grid");
    grid.innerHTML = "";
    const total = catalog.characters.length;
    document.getElementById("collection-count").textContent =
        `${ownedCount(inventory)} / ${total}`;
    const active = activeCharacter(inventory, catalog);
    document.getElementById("collection-active-line").textContent = active
        ? `활성: ${inventory.owned[active.id].nickname} (${active.name_ko})`
        : "활성 캐릭터 없음";

    for (const ch of catalog.characters) {
        const cell = document.createElement("button");
        const owned = ownsCharacter(inventory, ch.id);
        cell.className = `collection-cell ${rarityClass(ch.rarity)} ${owned ? "owned" : "locked"}`;
        if (owned && inventory.active_id === ch.id) cell.classList.add("active");
        cell.innerHTML = owned
            ? `<img src="characters/${ch.id}.png" alt="${ch.name_ko}" /><div class="cell-name">${inventory.owned[ch.id].nickname}</div><div class="cell-rarity">${rarityStars(ch.rarity)}</div>`
            : `<div class="cell-locked">?</div><div class="cell-rarity">${rarityStars(ch.rarity)}</div>`;
        cell.onclick = () => {
            if (!owned) return;
            setActive(inventory, ch.id);
            renderActiveCharacter();
            openRename(ch.id, ch.name_ko, openCollection);
        };
        grid.appendChild(cell);
    }
    showModal("collection-modal");

    document.querySelectorAll('[data-action="close-collection"]').forEach((b) => {
        b.onclick = () => hideModal("collection-modal");
    });
}

// ============== MODAL ==============

function showModal(id) {
    document.getElementById(id).classList.remove("hidden");
}
function hideModal(id) {
    document.getElementById(id).classList.add("hidden");
}

// ============== BOOT ==============

window.addEventListener("DOMContentLoaded", async () => {
    try {
        catalog = await loadCatalog();
    } catch (e) {
        console.error("failed to load catalog", e);
        return;
    }
    inventory = loadInventory();

    setupContextMenu();
    setupSlangy();
    setConnected(false);

    if (inventory.first_launch || ownedCount(inventory) === 0) {
        inventory.first_launch = false;
        saveInventory(inventory);
        openWelcome();
    } else {
        renderActiveCharacter();
    }

    document.getElementById("hud-tickets").textContent = `🎟 ${inventory.tickets}`;

    // Bridge tray events from Rust side (lib.rs dispatches them via .eval)
    window.addEventListener("tray:gacha", () => tryGacha());
    window.addEventListener("tray:collection", () => openCollection());

    connect();
});
