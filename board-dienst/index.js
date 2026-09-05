// Board-Dienst: nimmt ein Passwort entgegen und schreibt damit BOARD_DATEN.json auf GitHub.
// Der GitHub-Schlüssel liegt nur hier als Cloudflare-Secret — er erreicht nie den Browser.
const REPO = "mantyga777-coder/caliante-inspo-board";
const DATEI = "BOARD_DATEN.json";
const HERKUNFT = "https://mantyga777-coder.github.io";
const FELDER = ["kategorien", "status", "notiz", "ausgeblendet"];

// Zwischenlager für hochgeladene Dateien: ein GitHub-Release mit diesem Namensschild.
const TAG = "eingang";
// Cloudflare lässt höchstens 100 MB durch — 95 MB als Grenze, damit die Absage von uns
// kommt und nicht als unverständlicher Abbruch mitten im Hochladen.
const MAX_BYTES = 95 * 1024 * 1024;
// Was verarbeitet werden kann. .heic fehlt mit Absicht: ffmpeg auf GitHub kann es nicht.
const ENDUNGEN = [".mp4", ".mov", ".webm", ".m4v", ".mkv", ".jpg", ".jpeg", ".png", ".webp"];

const CORS = {
  "Access-Control-Allow-Origin": HERKUNFT,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Board-Passwort",
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

// Felix sieht diese Sätze im Board — deshalb keine Fehlernummern ohne Erklärung.
function githubFehler(status) {
  if (status === 401 || status === 403)
    return "Der Zugang zu GitHub ist abgelaufen — Felix muss einen neuen Schlüssel hinterlegen.";
  return `GitHub antwortet gerade nicht (${status}). Bitte in ein paar Minuten nochmal.`;
}

// Vertrag D: erlaubt sind nur A-Z a-z 0-9 . _ - , alles andere wird zu "_".
// Die 120 Zeichen gelten für den fertigen Namen samt Vorsatz, denn genau so landet er im
// Ordner eingang/ und wird dort erneut auf 120 gekürzt. Gekürzt wird deshalb hier schon der
// Namensteil und nie die Endung — ohne Endung würde die Datei drüben aussortiert.
function endgueltigerName(rohName, endung, slot) {
  const zeit = new Date().toISOString().replace(/[-:]/g, ""); // 20260905T161422.000Z
  const zufall = [...crypto.getRandomValues(new Uint8Array(3))]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  let vorsatz = `${zeit.slice(0, 8)}-${zeit.slice(9, 15)}-${zufall}_`;

  // Mehrere Bilder sollen EINE Karte zum Durchswipen werden. Jede Datei reist aber
  // einzeln hierher, deshalb wandert der Kartenname in den Dateinamen — er ist der
  // einzige Kanal, den beide Seiten schon kennen. eingang_verarbeiten.py liest ihn
  // wieder heraus und legt alle Bilder mit demselben Kartennamen zusammen.
  // Bindestriche sind im Kartennamen verboten, damit "-name-" eindeutig trennt.
  if (slot) {
    const sauber = slot.replace(/[^A-Za-z0-9._]/g, "_").slice(0, 40);
    if (sauber) vorsatz += `slot-${sauber}-name-`;
  }

  const basis =
    rohName.slice(0, rohName.length - endung.length).replace(/[^A-Za-z0-9._-]/g, "_") || "datei";
  return vorsatz + basis.slice(0, 120 - vorsatz.length - endung.length) + endung;
}

// Der Ablageort ist ein Release mit dem Namensschild "eingang". Er wird gesucht und
// notfalls neu angelegt — auf eine feste Nummer ist kein Verlass, jemand kann ihn löschen.
async function eingangsRelease(kopf) {
  const suchen = () =>
    fetch(`https://api.github.com/repos/${REPO}/releases/tags/${TAG}`, { headers: kopf });

  let da = await suchen();
  if (da.ok) return { release: await da.json() };
  if (da.status !== 404) return { fehler: githubFehler(da.status) };

  const angelegt = await fetch(`https://api.github.com/repos/${REPO}/releases`, {
    method: "POST",
    headers: { ...kopf, "Content-Type": "application/json" },
    body: JSON.stringify({
      tag_name: TAG,
      name: "Eingang",
      body: "Ablage für frisch hochgeladene Dateien. Wird nach der Verarbeitung geleert.",
    }),
  });
  if (angelegt.ok) return { release: await angelegt.json() };

  // Laden zwei Leute gleichzeitig hoch, legt der eine den Ablageort an und der andere
  // bekommt "gibt es schon" — dann reicht es, ihn einfach noch einmal zu suchen.
  da = await suchen();
  if (da.ok) return { release: await da.json() };
  return { fehler: githubFehler(angelegt.status) };
}

// Beim Hochladen steht das Passwort in der Kopfzeile und wird geprüft, BEVOR der Rumpf
// angefasst wird: der Rumpf ist ein Video, und dieser Dienst hat weder Speicher noch
// Rechenzeit, um es auch nur einmal komplett zu lesen. Er reicht es nur durch.
async function hochladen(request, env, adresse) {
  // Der Browser kodiert das Passwort, weil HTTP-Kopfzeilen nur Latin-1 tragen und ein
  // Umlaut setRequestHeader() sonst abbrechen lässt. Hier also wieder auspacken.
  let eingabe = request.headers.get("X-Board-Passwort") || "";
  try {
    eingabe = decodeURIComponent(eingabe);
  } catch (e) {
    // Kaputte Kodierung: unverändert weiterreichen, die Prüfung schlägt dann sauber fehl.
  }
  if (!(await passwortStimmt(eingabe, env.BOARD_PASSWORT)))
    return antwort({ ok: false, fehler: "Passwort stimmt nicht." }, 401);

  // Die Länge muss von vornherein feststehen: GitHub nimmt den Strom sonst nicht an.
  const laenge = Number(request.headers.get("Content-Length"));
  if (!Number.isInteger(laenge) || laenge <= 0)
    return antwort({ ok: false, fehler: "Die Datei ist leer oder kam nicht vollständig an." }, 400);
  if (laenge > MAX_BYTES)
    return antwort(
      {
        ok: false,
        fehler:
          "Diese Datei ist zu groß — mehr als 95 MB gehen nicht durch. Bitte eine kürzere oder kleinere Fassung hochladen.",
      },
      413
    );

  const rohName = (adresse.searchParams.get("name") || "").trim();
  const endung = ENDUNGEN.find((e) => rohName.toLowerCase().endsWith(e));
  if (!endung)
    return antwort(
      {
        ok: false,
        fehler:
          "Mit dieser Datei kann das Board nichts anfangen. Es gehen Videos (mp4, mov, webm, m4v, mkv) und Bilder (jpg, png, webp).",
      },
      400
    );

  const name = endgueltigerName(rohName, endung, (adresse.searchParams.get("slot") || "").trim());
  const kopf = {
    Authorization: "Bearer " + env.GH_TOKEN,
    Accept: "application/vnd.github+json",
    "User-Agent": "caliante-board-dienst",
  };

  const { release, fehler } = await eingangsRelease(kopf);
  if (fehler) return antwort({ ok: false, fehler }, 502);

  // FixedLengthStream statt eines gewöhnlichen Stroms: Cloudflare würde die Daten sonst in
  // Häppchen ohne Längenangabe verschicken, und genau das lehnt uploads.github.com ab.
  const durchreiche = new FixedLengthStream(laenge);
  // Bewusst ohne await — erst das fetch unten holt die Daten ab. Ein await hier würde
  // warten, bis der Strom leer ist, und das passiert nie, weil niemand ihn liest.
  request.body.pipeTo(durchreiche.writable).catch(() => {});

  const hoch = await fetch(
    `https://uploads.github.com/repos/${REPO}/releases/${release.id}/assets?name=${encodeURIComponent(name)}`,
    {
      method: "POST",
      headers: { ...kopf, "Content-Type": "application/octet-stream" },
      body: durchreiche.readable,
    }
  );
  if (!hoch.ok) return antwort({ ok: false, fehler: githubFehler(hoch.status) }, 502);

  // Anklopfen: die Datei liegt bereit, jetzt darf GitHub sie verarbeiten.
  const anklopfen = await fetch(`https://api.github.com/repos/${REPO}/dispatches`, {
    method: "POST",
    headers: { ...kopf, "Content-Type": "application/json" },
    body: JSON.stringify({ event_type: "neuer-upload" }),
  });
  // Die Datei ist sicher angekommen, aber ohne Anklopfen passiert nichts weiter — das
  // muss Felix erfahren, sonst wartet er vergeblich darauf, dass sie im Board auftaucht.
  if (!anklopfen.ok)
    return antwort(
      {
        ok: false,
        fehler:
          "Die Datei ist angekommen, aber das Board baut sich gerade nicht von allein neu. Bitte Felix Bescheid geben.",
      },
      502
    );

  return antwort({ ok: true, datei: name });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (request.method !== "POST") return antwort({ ok: false, fehler: "Nur POST." }, 405);

    const adresse = new URL(request.url);
    const pfad = adresse.pathname;
    if (pfad !== "/anmelden" && pfad !== "/speichern" && pfad !== "/hochladen")
      return antwort({ ok: false, fehler: "Unbekannt." }, 404);

    const ip = request.headers.get("CF-Connecting-IP") || "unbekannt";

    // Das Hochladen läuft vor allem anderen ab: unten wird immer erst der Rumpf gelesen,
    // und ein Video darf hier nicht gelesen werden.
    if (pfad === "/hochladen") {
      // Eine eigene Bremse mit eigenem Zähler: eine Bilderserie sind viele Anfragen kurz
      // hintereinander, ein Passwortversuch nicht. Fehlt LIMIT_HOCHLADEN noch in
      // wrangler.toml, greift ersatzweise die alte Bremse — dann zwar knapp, aber die
      // Uploads blockieren wenigstens nicht die Anmeldung.
      const bremse = env.LIMIT_HOCHLADEN || env.LIMIT;
      const { success } = await bremse.limit({ key: "hochladen:" + ip });
      if (!success)
        return antwort(
          {
            ok: false,
            fehler:
              "Es kamen gerade sehr viele Dateien auf einmal. Bitte eine Minute warten und den Rest noch einmal hochladen.",
          },
          429
        );
      try {
        return await hochladen(request, env, adresse);
      } catch (e) {
        return antwort({ ok: false, fehler: "Das Hochladen hat nicht geklappt. Bitte noch einmal versuchen." }, 502);
      }
    }

    // Bremse gegen Passwort-Raten, pro Absender.
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
