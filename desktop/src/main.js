// tteoki — chibi-mcp pet runtime.
//
// 1. Loads the base SVG character from characters/<id>/base.svg.
// 2. Connects to the MCP server's WebSocket (ws://127.0.0.1:9876).
// 3. Translates server messages into:
//      - data-mood attribute (CSS handles tinting)
//      - face element edits (eyes + mouth shape per mood)
//      - body width growth based on session time
//      - speech bubble + slice animation events
//
// Character slot: the SVG is loaded by id from `characters/<id>/base.svg`.
// To swap to a new character (e.g., an illustrator's PNG/SVG), set
// CHARACTER_ID below or store user preference later.

const CHARACTER_ID = "garaetteok";
const WS_URL = "ws://127.0.0.1:9876";
// Exponential backoff: 2s → 4s → 8s → 16s → 30s (cap).
// Prevents tight reconnect loop when server is intentionally offline.
const RECONNECT_INITIAL_MS = 2000;
const RECONNECT_MAX_MS = 30000;
const RECONNECT_BACKOFF = 2.0;

// === MOOD → face geometry ===
// All coords align to characters/garaetteok/meta.json face_anchor.
const FACES = {
    calm: {
        eyes: (g) => drawEyes(g, { kind: "round" }),
        mouth: "M 512 120 Q 534 130 556 120",
        mouth_inner: "M 518 122 Q 534 130 550 122",
    },
    happy: {
        eyes: (g) => drawEyes(g, { kind: "crescent_up" }),
        mouth: "M 508 116 Q 534 142 560 116",
        mouth_inner: "M 514 120 Q 534 138 554 120",
    },
    panting: {
        eyes: (g) => drawEyes(g, { kind: "round", rx: 6, ry: 7 }),
        mouth: "M 528 118 a 6 7 0 1 0 12 0 a 6 7 0 1 0 -12 0",  // open O
        mouth_inner: null,
    },
    drowsy: {
        eyes: (g) => drawEyes(g, { kind: "closed" }),
        mouth: "M 512 124 q 5 -3 10 0 q 5 3 10 0 q 5 -3 10 0",
        mouth_inner: null,
    },
    lonely: {
        eyes: (g) => drawEyes(g, { kind: "small_dot" }),
        mouth: "M 514 130 Q 534 118 554 130",
        mouth_inner: null,
    },
    surprised: {
        eyes: (g) => drawEyes(g, { kind: "round", rx: 11, ry: 13 }),
        mouth: "M 525 116 a 9 11 0 1 0 18 0 a 9 11 0 1 0 -18 0",
        mouth_inner: null,
    },
    joyful: {
        eyes: (g) => drawEyes(g, { kind: "star" }),
        mouth: "M 506 114 Q 534 148 562 114",
        mouth_inner: "M 514 118 Q 534 142 554 118",
    },
};

function drawEyes(eyesGroup, opts) {
    eyesGroup.innerHTML = "";
    const left = { cx: 500, cy: 98 };
    const right = { cx: 568, cy: 98 };

    const make = (anchor) => {
        if (opts.kind === "round") {
            const rx = opts.rx ?? 9.5;
            const ry = opts.ry ?? 11.5;
            eyesGroup.append(
                el("ellipse", { cx: anchor.cx, cy: anchor.cy, rx, ry, fill: "url(#eyeFill)" }),
                el("ellipse", { cx: anchor.cx + 4, cy: anchor.cy - 6, rx: 4, ry: 4.5, fill: "#FFFFFF", opacity: 0.98 }),
                el("ellipse", { cx: anchor.cx - 4, cy: anchor.cy + 5, rx: 1.8, ry: 2, fill: "#FFFFFF", opacity: 0.5 }),
            );
        } else if (opts.kind === "crescent_up") {
            eyesGroup.append(
                el("path", {
                    d: `M ${anchor.cx - 10} ${anchor.cy + 2} Q ${anchor.cx} ${anchor.cy - 12} ${anchor.cx + 10} ${anchor.cy + 2}`,
                    stroke: "#1F1410", "stroke-width": 4, fill: "none", "stroke-linecap": "round",
                }),
            );
        } else if (opts.kind === "closed") {
            eyesGroup.append(
                el("path", {
                    d: `M ${anchor.cx - 10} ${anchor.cy + 2} Q ${anchor.cx} ${anchor.cy + 8} ${anchor.cx + 10} ${anchor.cy + 2}`,
                    stroke: "#1F1410", "stroke-width": 3.5, fill: "none", "stroke-linecap": "round",
                }),
            );
        } else if (opts.kind === "small_dot") {
            eyesGroup.append(
                el("circle", { cx: anchor.cx, cy: anchor.cy + 2, r: 3.5, fill: "#1F1410" }),
            );
        } else if (opts.kind === "star") {
            const starPath = starPathD(anchor.cx, anchor.cy, 5, 11, 4);
            eyesGroup.append(
                el("path", { d: starPath, fill: "#FFCB3D", stroke: "#A06200", "stroke-width": 1.5 }),
            );
        }
    };

    make(left);
    make(right);
}

function starPathD(cx, cy, points, outerR, innerR) {
    const arr = [];
    const step = Math.PI / points;
    for (let i = 0; i < points * 2; i++) {
        const r = i % 2 === 0 ? outerR : innerR;
        const a = i * step - Math.PI / 2;
        const x = cx + r * Math.cos(a);
        const y = cy + r * Math.sin(a);
        arr.push(`${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`);
    }
    arr.push("Z");
    return arr.join(" ");
}

function el(tag, attrs) {
    const ns = "http://www.w3.org/2000/svg";
    const n = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
}

// === LENGTH GROWTH (deferred to v0.2) ===
// Body length will grow linearly with session seconds. For v0.1 the window is
// fixed-size so the visual growth is handled by the slice cycle alone.

// === SLICE ANIMATION ===
const board = () => document.getElementById("board");
let pieceIdCounter = 0;

function dropSlicePiece() {
    const piece = document.createElement("div");
    piece.className = "slice-piece";
    piece.dataset.id = String(++pieceIdCounter);
    // Spread pieces across cutting board horizontally
    const x = 30 + Math.random() * (window.innerWidth - 90);
    piece.style.left = `${x}px`;
    board().appendChild(piece);
    // Auto-remove after fade (5s total = 0.5s drop + 4.5s wait + ...)
    setTimeout(() => piece.remove(), 5500);
}

function animateKnife() {
    const k = document.getElementById("knife");
    if (!k) return;
    k.classList.remove("hidden", "slice-anim");
    // force reflow then re-add class so animation restarts
    void k.getBoundingClientRect();
    k.classList.add("slice-anim");
    setTimeout(() => k.classList.add("hidden"), 700);
}

// === SYRUP DRIP DYNAMIC RATE ===
// Spawn an extra drip droplet element periodically depending on mood.
let dripTimer = null;

function setDripCadence(seconds) {
    if (dripTimer) clearInterval(dripTimer);
    if (!seconds || seconds <= 0) return;
    dripTimer = setInterval(spawnDrip, seconds * 1000);
}

function spawnDrip() {
    const layer = document.getElementById("syrup-layer");
    if (!layer) return;
    const drop = el("ellipse", {
        cx: 239, cy: 80, rx: 4, ry: 6,
        fill: "url(#syrupMain)",
        class: "syrup-drip",
    });
    layer.appendChild(drop);
    setTimeout(() => drop.remove(), 1700);
}

// === SPEECH BUBBLE ===
let speechTimer = null;
function speak(text) {
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

// === HUD ===
function updateHud(state) {
    document.getElementById("hud-mood").textContent = state.mood ?? "—";
    const c = state.counters ?? {};
    document.getElementById("hud-slices").textContent = `${c.slices_today ?? 0}도막`;
    document.getElementById("hud-calls").textContent =
        `${c.calls_since_slice ?? 0}/${c.slice_interval ?? "?"}`;
}

// === MOOD APPLICATION ===
let prevMood = null;
function applyMood(mood) {
    if (!FACES[mood]) mood = "calm";
    const stage = document.getElementById("stage");
    stage.dataset.mood = mood;

    const eyesGroup = document.getElementById("eyes");
    const mouth = document.getElementById("mouth");
    const mouthInner = document.getElementById("mouth-inner");

    const def = FACES[mood];
    if (eyesGroup) def.eyes(eyesGroup);
    if (mouth) mouth.setAttribute("d", def.mouth);
    if (mouthInner) {
        if (def.mouth_inner) {
            mouthInner.setAttribute("d", def.mouth_inner);
            mouthInner.style.display = "";
        } else {
            mouthInner.style.display = "none";
        }
    }

    // Bounce/splat one-shots on certain transitions
    const tteoki = document.getElementById("tteoki");
    if (mood === "happy" && prevMood !== "happy") flash(tteoki, "bounce", 550);
    if (mood === "surprised" && prevMood !== "surprised") flash(tteoki, "splat", 400);

    // Adjust drip cadence based on CPU/mood
    if (mood === "panting") setDripCadence(1.0);
    else if (mood === "drowsy" || mood === "lonely") setDripCadence(0);
    else setDripCadence(4.0);

    prevMood = mood;
}

function flash(elem, cls, ms) {
    elem.classList.remove(cls);
    void elem.getBoundingClientRect();
    elem.classList.add(cls);
    setTimeout(() => elem.classList.remove(cls), ms);
}

// === WebSocket connection (with exponential backoff) ===
let ws = null;
let reconnectScheduled = false;
let reconnectDelay = RECONNECT_INITIAL_MS;

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
        reconnectDelay = RECONNECT_INITIAL_MS;  // reset backoff on success
    };
    ws.onclose = () => {
        setConnected(false);
        scheduleReconnect();
    };
    ws.onerror = () => {
        // onclose will handle reconnect
    };
    ws.onmessage = (evt) => {
        try {
            const msg = JSON.parse(evt.data);
            handleMessage(msg);
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
    const stage = document.getElementById("stage");
    stage.dataset.connected = ok ? "true" : "false";
    if (!ok) document.getElementById("hud-mood").textContent = "offline";
}

function handleMessage(msg) {
    if (msg.type === "state") {
        const payload = msg.payload ?? {};
        applyMood(payload.mood);
        updateHud(payload);
    } else if (msg.type === "say") {
        speak(msg.text ?? "");
    } else if (msg.type === "slice") {
        animateKnife();
        dropSlicePiece();
    }
}

// === BOOT ===
async function loadCharacter(id) {
    const resp = await fetch(`characters/${id}/base.svg`);
    if (!resp.ok) throw new Error(`failed to load character ${id}`);
    const svgText = await resp.text();
    const placeholder = document.getElementById("tteoki-placeholder");
    if (!placeholder) return;
    // Replace placeholder with loaded SVG
    placeholder.outerHTML = svgText;
    // After injection, set common ids so the face/body groups are addressable
    const tteoki = document.querySelector("svg");
    if (tteoki) tteoki.id = "tteoki";
}

window.addEventListener("DOMContentLoaded", async () => {
    try {
        await loadCharacter(CHARACTER_ID);
    } catch (e) {
        console.error(e);
    }
    applyMood("calm");
    updateHud({ mood: "calm", counters: { slices_today: 0, calls_since_slice: 0, slice_interval: 10 } });
    setConnected(false);
    connect();
});
