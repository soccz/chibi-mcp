// inventory.js — localStorage-backed character collection + gacha system.

const STORAGE_KEY = "chibi.inventory.v1";

const RARITY_WEIGHTS = { 5: 1, 4: 5, 3: 24, 2: 70 };

let _meta = null;

export async function loadCatalog() {
    if (_meta) return _meta;
    const resp = await fetch("characters/meta.json");
    if (!resp.ok) throw new Error("character catalog missing");
    _meta = await resp.json();
    return _meta;
}

export function loadInventory() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
    } catch {
        /* corrupted — start fresh */
    }
    return {
        owned: {},          // id → { id, nickname, obtained_at }
        active_id: null,
        tickets: 0,
        first_launch: true,
        last_daily_ticket: null,
        slices_at_last_ticket: 0,
        calls_at_last_ticket: 0,
    };
}

export function saveInventory(inv) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(inv));
}

export function ownsCharacter(inv, id) {
    return Boolean(inv.owned[id]);
}

export function ownedCount(inv) {
    return Object.keys(inv.owned).length;
}

export function addCharacter(inv, ch, nickname = null) {
    inv.owned[ch.id] = {
        id: ch.id,
        nickname: nickname ?? ch.name_ko,
        obtained_at: new Date().toISOString(),
    };
    if (!inv.active_id) inv.active_id = ch.id;
    saveInventory(inv);
    return inv;
}

export function renameCharacter(inv, id, nickname) {
    if (!inv.owned[id]) return false;
    inv.owned[id].nickname = nickname?.trim() || inv.owned[id].nickname;
    saveInventory(inv);
    return true;
}

export function setActive(inv, id) {
    if (!inv.owned[id]) return false;
    inv.active_id = id;
    saveInventory(inv);
    return true;
}

export function activeCharacter(inv, catalog) {
    if (!inv.active_id) return null;
    return catalog.characters.find((c) => c.id === inv.active_id) ?? null;
}

export function characterById(catalog, id) {
    return catalog.characters.find((c) => c.id === id) ?? null;
}

export function consumeTicket(inv) {
    if (inv.tickets <= 0) return false;
    inv.tickets -= 1;
    saveInventory(inv);
    return true;
}

export function grantTicket(inv, n = 1) {
    inv.tickets += n;
    saveInventory(inv);
}

// === Gacha ===
export function drawGacha(catalog) {
    const total = Object.values(RARITY_WEIGHTS).reduce((a, b) => a + b, 0);
    let roll = Math.random() * total;
    let pickedRarity = 2;
    for (const [r, w] of Object.entries(RARITY_WEIGHTS)) {
        roll -= w;
        if (roll <= 0) {
            pickedRarity = parseInt(r, 10);
            break;
        }
    }
    const pool = catalog.characters.filter((c) => c.rarity === pickedRarity);
    const safe = pool.length > 0 ? pool : catalog.characters;
    return safe[Math.floor(Math.random() * safe.length)];
}

// === Ticket grant rules ===
// Daily: 1 per calendar day (first call after midnight local).
// Every 100 calls: +1.
// Every 10 slices: +1.
export function evaluateTicketGrants(inv, currentCounters) {
    let granted = 0;
    const today = new Date().toISOString().slice(0, 10);
    if (inv.last_daily_ticket !== today) {
        inv.tickets += 1;
        inv.last_daily_ticket = today;
        granted += 1;
    }
    const calls = currentCounters?.calls_total ?? 0;
    const callBuckets = Math.floor(calls / 100) - Math.floor(inv.calls_at_last_ticket / 100);
    if (callBuckets > 0) {
        inv.tickets += callBuckets;
        inv.calls_at_last_ticket = calls;
        granted += callBuckets;
    }
    const slices = currentCounters?.slices_today ?? 0;
    const sliceBuckets = Math.floor(slices / 10) - Math.floor(inv.slices_at_last_ticket / 10);
    if (sliceBuckets > 0) {
        inv.tickets += sliceBuckets;
        inv.slices_at_last_ticket = slices;
        granted += sliceBuckets;
    }
    if (granted > 0) saveInventory(inv);
    return granted;
}

export function rarityStars(n) {
    return "★".repeat(n) + "☆".repeat(5 - n);
}

export function rarityClass(n) {
    return `rarity-${n}`;
}
