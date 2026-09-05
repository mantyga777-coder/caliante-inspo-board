// Board-Dienst: nimmt ein Passwort entgegen und schreibt damit BOARD_DATEN.json auf GitHub.
// Der GitHub-Schlüssel liegt nur hier als Cloudflare-Secret — er erreicht nie den Browser.
const REPO = "mantyga777-coder/caliante-inspo-board";
const DATEI = "BOARD_DATEN.json";
const HERKUNFT = "https://mantyga777-coder.github.io";
const FELDER = ["kategorien", "status", "notiz", "ausgeblendet"];

const CORS = {
  "Access-Control-Allow-Origin": HERKUNFT,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

const antwort = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });

async function passwortStimmt(eingabe, echt) {
  if (typeof eingabe !== "string" || !eingabe || !echt) return false;
  const kodierer = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", kodierer.encode(eingabe)),
    crypto.subtle.digest("SHA-256", kodierer.encode(echt)),
  ]);
  return crypto.subtle.timingSafeEqual(a, b);
}

function vonBase64(s) {
  const bin = atob(s.replace(/\s/g, ""));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

function nachBase64(text) {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

// Der Browser darf nur genau die vier bekannten Felder setzen — sonst könnte ein Fehler
// (oder jemand mit dem Passwort) beliebige Daten in die Datei schreiben.
function saubereAenderungen(roh) {
  if (!roh || typeof roh !== "object" || Array.isArray(roh)) return null;
  const ids = Object.keys(roh);
  if (ids.length > 5000) return null;
  const raus = {};
  for (const id of ids) {
    if (id.length > 300) return null;
    const w = roh[id];
    if (!w || typeof w !== "object" || Array.isArray(w)) return null;
    const e = {};
    if (Array.isArray(w.kategorien)) {
      const k = w.kategorien
        .filter((x) => typeof x === "string" && x && x.length <= 120)
        .slice(0, 50);
      if (k.length) e.kategorien = k;
    }
    if (typeof w.status === "string" && w.status) e.status = w.status.slice(0, 120);
    if (typeof w.notiz === "string" && w.notiz) e.notiz = w.notiz.slice(0, 4000);
    if (w.ausgeblendet === true) e.ausgeblendet = true;
    raus[id] = e;
  }
  return raus;
}

function saubereKategorien(roh) {
  if (!Array.isArray(roh)) return null;
  return roh.filter((x) => typeof x === "string" && x && x.length <= 120).slice(0, 200);
}

async function speichern(env, aenderungen, kategorien) {
  const url = `https://api.github.com/repos/${REPO}/contents/${DATEI}`;
  const kopf = {
    Authorization: "Bearer " + env.GH_TOKEN,
    Accept: "application/vnd.github+json",
    "User-Agent": "caliante-board-dienst",
  };

  // Erst den aktuellen Stand holen, sonst überschreiben wir fremde Änderungen.
  const jetzt = await fetch(url, { headers: kopf });
  if (jetzt.status === 401 || jetzt.status === 403)
    return { ok: false, fehler: "Der Board-Dienst hat kein Schreibrecht mehr auf GitHub." };
  if (!jetzt.ok) return { ok: false, fehler: `GitHub antwortet nicht (${jetzt.status}).` };
  const datei = await jetzt.json();

  let bestand;
  try {
    bestand = JSON.parse(vonBase64(datei.content));
  } catch (e) {
    return { ok: false, fehler: "BOARD_DATEN.json auf GitHub ist beschädigt." };
  }

  const eintraege = bestand.eintraege || {};
  for (const [id, werte] of Object.entries(aenderungen)) {
    if (Object.keys(werte).length) eintraege[id] = werte;
    else delete eintraege[id];
  }

  const inhalt = nachBase64(JSON.stringify({ kategorien, eintraege }, null, 2));
  const put = await fetch(url, {
    method: "PUT",
    headers: { ...kopf, "Content-Type": "application/json" },
    body: JSON.stringify({ message: "Board online bearbeitet", content: inhalt, sha: datei.sha }),
  });
  if (put.status === 409)
    return { ok: false, fehler: "Jemand anderes hat gerade gespeichert. Seite neu laden und nochmal versuchen." };
  if (!put.ok) return { ok: false, fehler: `Speichern abgelehnt (${put.status}).` };
  return { ok: true };
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (request.method !== "POST") return antwort({ ok: false, fehler: "Nur POST." }, 405);

    const pfad = new URL(request.url).pathname;
    if (pfad !== "/anmelden" && pfad !== "/speichern")
      return antwort({ ok: false, fehler: "Unbekannt." }, 404);

    // Bremse gegen Passwort-Raten, pro Absender.
    const ip = request.headers.get("CF-Connecting-IP") || "unbekannt";
    const { success } = await env.LIMIT.limit({ key: ip });
    if (!success) return antwort({ ok: false, fehler: "Zu viele Versuche. Bitte kurz warten." }, 429);

    let daten;
    try {
      daten = await request.json();
    } catch (e) {
      return antwort({ ok: false, fehler: "Ungültige Anfrage." }, 400);
    }

    if (!(await passwortStimmt(daten.passwort, env.BOARD_PASSWORT)))
      return antwort({ ok: false, fehler: "Passwort stimmt nicht." }, 401);

    if (pfad === "/anmelden") return antwort({ ok: true });

    const aenderungen = saubereAenderungen(daten.aenderungen);
    const kategorien = saubereKategorien(daten.kategorien);
    if (!aenderungen || !kategorien)
      return antwort({ ok: false, fehler: "Ungültige Daten." }, 400);

    try {
      const ergebnis = await speichern(env, aenderungen, kategorien);
      return antwort(ergebnis, ergebnis.ok ? 200 : 502);
    } catch (e) {
      return antwort({ ok: false, fehler: "Keine Verbindung zu GitHub." }, 502);
    }
  },
};
