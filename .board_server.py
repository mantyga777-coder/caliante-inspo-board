#!/usr/bin/env python3
"""Lokaler Board-Server — nur damit kann das Board Dateien hochladen und Themen speichern.
Start per Doppelklick auf BOARD_STARTEN.command. Läuft ausschließlich auf diesem Mac
(127.0.0.1), niemand von außen kommt dran."""
import http.server, os, json, re, shutil, subprocess, sys, urllib.parse, webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOADS = os.path.join(BASE, "INSPO_INBOX", "videos")
BILDER = os.path.join(BASE, "INSPO_INBOX", "bilder")
TRASH = os.path.join(BASE, "_papierkorb")
DATEN = os.path.join(BASE, "BOARD_DATEN.json")
VIDEO_EXT = ('.mp4','.mov','.webm','.m4v')
BILD_EXT = ('.jpg','.jpeg','.png','.heic','.webp')
PORT = 8777
MAX_MB = 500

def rebuild():
    subprocess.run([sys.executable, os.path.join(BASE,".build_board.py")], cwd=BASE, check=True)

def daten_lesen():
    try:
        d = json.load(open(DATEN, encoding='utf-8'))
    except Exception:
        d = {}
    d.setdefault("kategorien", [])
    d.setdefault("eintraege", {})
    return d

def daten_schreiben(d):
    tmp = DATEN + ".tmp"          # erst daneben schreiben, dann umbenennen —
    with open(tmp, "w", encoding='utf-8') as f:   # so bleibt bei einem Absturz die alte Datei heil
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATEN)

def safe_name(n):
    n = re.sub(r'[^A-Za-z0-9._ -]', '_', os.path.basename(n)).lstrip('.')
    return n[:120] or "video.mp4"

def frei(pfad):
    stem, ext = os.path.splitext(pfad); i = 2
    while os.path.exists(pfad):
        pfad = f"{stem}-{i}{ext}"; i += 1
    return pfad

def innerhalb(pfad, wurzel):
    pfad, wurzel = os.path.realpath(pfad), os.path.realpath(wurzel)
    return pfad == wurzel or pfad.startswith(wurzel + os.sep)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=BASE, **kw)

    def log_message(self, fmt, *args):
        pass  # Terminalfenster ruhig halten

    def antwort(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def rumpf(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path == "/upload":
                self.hochladen(q.get("name",""), q.get("kat",""), q.get("slot",""))
            elif u.path == "/entfernen":
                self.entfernen(urllib.parse.unquote(q.get("id","")))
            elif u.path == "/zurueckholen":
                self.zurueckholen(urllib.parse.unquote(q.get("id","")))
            elif u.path == "/daten":
                self.daten_speichern()
            else:
                self.antwort({"ok": False, "fehler": "Unbekannter Befehl."}, 404)
        except Exception as e:
            self.antwort({"ok": False, "fehler": str(e)}, 500)

    def daten_speichern(self):
        """Das Board schickt seinen Stand — Einträge, die es nicht kennt (z.B. gerade per
        Hochladen oder aus einem anderen Tab entstanden), bleiben unangetastet erhalten."""
        neu = json.loads(self.rumpf().decode('utf-8'))
        kats = [str(k).strip() for k in neu.get("kategorien", []) if str(k).strip()]
        if not kats:
            return self.antwort({"ok": False, "fehler": "Mindestens ein Thema muss bleiben."}, 400)
        if len(kats) != len(set(kats)):
            return self.antwort({"ok": False, "fehler": "Zwei Themen heißen gleich."}, 400)
        eintraege = daten_lesen()["eintraege"]
        for k, v in (neu.get("eintraege") or {}).items():
            if not isinstance(v, dict): continue
            gefiltert = {f: v[f] for f in ("kategorien","status","notiz","ausgeblendet") if v.get(f)}
            if gefiltert: eintraege[str(k)] = gefiltert
            else: eintraege.pop(str(k), None)
        daten_schreiben({"kategorien": kats, "eintraege": eintraege})
        rebuild()
        self.antwort({"ok": True, "themen": len(kats), "eintraege": len(eintraege)})

    def hochladen(self, name, kat, slot):
        n = safe_name(urllib.parse.unquote(name))
        ist_bild = n.lower().endswith(BILD_EXT)
        if not ist_bild and not n.lower().endswith(VIDEO_EXT):
            return self.antwort({"ok": False, "fehler": "Nur Videos (mp4, mov, webm, m4v) "
                                                        "oder Bilder (jpg, png, heic, webp)."}, 400)
        laenge = int(self.headers.get("Content-Length", 0))
        if laenge <= 0 or laenge > MAX_MB * 1048576:
            return self.antwort({"ok": False, "fehler": f"Datei ist leer oder größer als {MAX_MB} MB."}, 400)
        if ist_bild:
            # Bilder wandern in einen Slot-Ordner — der ist im Board eine Karte zum Durchswipen.
            slot_name = safe_name(urllib.parse.unquote(slot)).rsplit('.',1)[0] or os.path.splitext(n)[0]
            ordner = os.path.join(BILDER, slot_name)
            eintrag_id = os.path.relpath(ordner, BASE)
        else:
            ordner = UPLOADS
            eintrag_id = None
        os.makedirs(ordner, exist_ok=True)
        ziel = frei(os.path.join(ordner, n))
        with open(ziel, "wb") as f:
            rest = laenge
            while rest > 0:
                stueck = self.rfile.read(min(1048576, rest))
                if not stueck: break
                f.write(stueck); rest -= len(stueck)
        kat = urllib.parse.unquote(kat).strip()
        if kat:
            d = daten_lesen()
            d["eintraege"].setdefault(eintrag_id or os.path.relpath(ziel, BASE), {})["kategorien"] = [kat]
            daten_schreiben(d)
        rebuild()
        self.antwort({"ok": True, "datei": os.path.basename(ziel), "kategorie": kat,
                      "slot": os.path.basename(ordner) if ist_bild else ""})

    def entfernen(self, rel):
        """Eigene Uploads wandern in den Papierkorb, Produktionsmaterial wird nur ausgeblendet."""
        if not rel:
            return self.antwort({"ok": False, "fehler": "Kein Eintrag angegeben."}, 400)
        voll = os.path.join(BASE, rel)
        # Eigene Uploads: einzelnes Video oder ein ganzer Bilder-Slot-Ordner.
        eigener_upload = rel.startswith("INSPO_INBOX" + os.sep) and innerhalb(voll, BASE) and (
            (os.path.isfile(voll) and rel.lower().endswith(VIDEO_EXT + BILD_EXT))
            or (os.path.isdir(voll) and rel.startswith(os.path.join("INSPO_INBOX","bilder") + os.sep)))
        if eigener_upload:
            ziel = frei(os.path.join(TRASH, rel))
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            shutil.move(voll, ziel)
            art = "papierkorb"
        else:
            d = daten_lesen()
            d["eintraege"].setdefault(rel, {})["ausgeblendet"] = True
            daten_schreiben(d)
            art = "ausgeblendet"
        rebuild()
        self.antwort({"ok": True, "art": art})

    def zurueckholen(self, rel):
        d = daten_lesen()
        eintrag = d["eintraege"].get(rel)
        if not eintrag or not eintrag.get("ausgeblendet"):
            return self.antwort({"ok": False, "fehler": "Der Eintrag ist gar nicht ausgeblendet."}, 400)
        eintrag.pop("ausgeblendet")
        if not eintrag: d["eintraege"].pop(rel)
        daten_schreiben(d)
        rebuild()
        self.antwort({"ok": True})

    def do_GET(self):
        # Safari verlangt Teilabrufe, sonst springt das Video nicht.
        bereich = self.headers.get("Range")
        pfad = self.translate_path(self.path)
        m = re.match(r"bytes=(\d+)-(\d*)", bereich or "")
        if m and os.path.isfile(pfad) and pfad.lower().endswith(VIDEO_EXT):
            groesse = os.path.getsize(pfad)
            start = int(m.group(1))
            ende = min(int(m.group(2)) if m.group(2) else groesse - 1, groesse - 1)
            if start >= groesse:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{groesse}")
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(pfad))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{ende}/{groesse}")
            self.send_header("Content-Length", str(ende - start + 1))
            self.end_headers()
            with open(pfad, "rb") as f:
                f.seek(start); rest = ende - start + 1
                while rest > 0:
                    stueck = f.read(min(65536, rest))
                    if not stueck: break
                    self.wfile.write(stueck); rest -= len(stueck)
            return
        super().do_GET()

if __name__ == "__main__":
    rebuild()
    adresse = f"http://localhost:{PORT}/CALIANTE_VIDEO_BOARD.html"
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"\n  Port {PORT} ist belegt — läuft das Board vielleicht schon?")
        print(f"  Dann einfach {adresse} im Browser öffnen.\n")
        sys.exit(1)
    print(f"\n  Board läuft: {adresse}")
    if os.environ.get("BOARD_STILL"):
        print("  Läuft im Hintergrund (LaunchAgent) — kein Fenster offen halten nötig.\n")
    else:
        print("  Dieses Fenster muss offen bleiben, solange du am Board arbeitest.")
        print("  Zum Beenden: Strg+C drücken oder Fenster schließen.\n")
        webbrowser.open(adresse)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Board beendet.\n")
