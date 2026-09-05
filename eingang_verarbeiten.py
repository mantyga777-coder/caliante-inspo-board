#!/usr/bin/env python3
"""Verarbeitet neu hochgeladene Dateien aus eingang/ — laeuft auf GitHub.

Fuer jede Datei: verkleinerte Web-Fassung erzeugen, Vorschaubild bauen, Eintrag in
eintraege.json aufnehmen, Original aus eingang/ entfernen. Danach baut render_web.py
die Seite neu. Ergibt dieselben Eintraege wie .build_board.py auf dem Mac.
"""
import base64, hashlib, json, os, re, subprocess, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
EINGANG = os.path.join(BASE, "eingang")
WEB = os.path.join(BASE, "web", "INSPO_INBOX")
EINTRAEGE = os.path.join(BASE, "eintraege.json")
VIDEO_EXT = ('.mp4', '.mov', '.webm', '.m4v', '.mkv')
# .heic fehlt hier mit Absicht: ffmpeg auf dem GitHub-Rechner kann es nicht oeffnen,
# solche Dateien wuerden den Ordner eingang/ sonst dauerhaft verstopfen.
BILD_EXT = ('.jpg', '.jpeg', '.png', '.webp')
# Der Dienst stellt jedem Upload Datum und Zufallsfolge voran (20260905-161422-a1b2c3_).
# Nur so bleiben zwei gleichnamige iPhone-Videos zwei verschiedene Karten. Fuer die
# Anzeige schneiden wir diesen Vorsatz wieder ab — in der Kennung bleibt er stehen.
VORSATZ = re.compile(r'^\d{8}-\d{6}-[A-Za-z0-9]{6}_')

def saeubern(n):
    """Nur A-Z a-z 0-9 . _ - zulassen, hoechstens 120 Zeichen — dieselbe Regel wie
    safe_name() im lokalen Server. Leerzeichen werden hier zusaetzlich ersetzt, weil der
    Dateiname unveraendert als Web-Adresse in die Seite geschrieben wird und dort abbricht."""
    n = re.sub(r'[^A-Za-z0-9._-]', '_', os.path.basename(n)).lstrip('.')
    return n[:120] or "video.mp4"

def lesbar(n):
    """Der Name, den das Team auf der Karte sieht — ohne den technischen Vorsatz."""
    return VORSATZ.sub('', n)

# Der Dienst schiebt "slot-<Kartenname>-name-" zwischen Vorsatz und Dateinamen, wenn
# mehrere Bilder zu einer Karte zum Durchswipen gehoeren sollen. Im Kartennamen sind
# Bindestriche verboten, deshalb trennt "-name-" eindeutig.
SLOTMUSTER = re.compile(r'^(\d{8}-\d{6}-[A-Za-z0-9]{6}_)slot-([A-Za-z0-9._]+)-name-(.+)$')

def slot_teile(n):
    """Zerlegt in (Kartenname, Dateiname ohne die Kartenname-Markierung).

    Ohne Markierung kommt ("", n) zurueck — dann wird das Bild wie bisher eine
    eigene Karte. Der Vorsatz bleibt im zweiten Teil stehen, damit die Bilddateien
    innerhalb einer Karte eindeutige Namen behalten."""
    m = SLOTMUSTER.match(n)
    if not m:
        return "", n
    return m.group(2), m.group(1) + m.group(3)

def echte_themen():
    """Die Themen, die es im Board wirklich gibt. Felix legt eigene an und loescht alte —
    die fest verdrahtete Liste in raten() ist deshalb regelmaessig veraltet."""
    try:
        with open(os.path.join(BASE, "BOARD_DATEN.json"), encoding='utf-8') as f:
            return [k for k in json.load(f).get("kategorien", []) if isinstance(k, str)]
    except Exception:
        return []


def guess(t):
    """Themenvorschlag aus dem Dateinamen, aber nur wenn es das Thema noch gibt.

    Sonst landet der Eintrag unter einem Namen, den die Seite beim Bauen wieder
    wegwirft (render_web.py behaelt nur bekannte Themen) — und das Video taucht
    unter 'Sonstiges' auf, ohne dass jemand versteht, warum."""
    vorschlag = raten(t)
    da = echte_themen()
    if not da or vorschlag in da:
        return vorschlag
    return "Sonstiges" if "Sonstiges" in da else da[-1]


def raten(t):
    """Themenvorschlag aus dem Dateinamen — gleiche Regeln wie im Mac-Generator."""
    t = t.lower()
    if any(k in t for k in ["unbox", "paket", "auspack"]): return "Unboxing"
    if any(k in t for k in ["mirror", "spiegel", "slideshow", "ootd"]): return "Spiegel-Slideshow"
    if any(k in t for k in ["street", "strasse", "city", "vespa", "outdoor"]): return "Street"
    if any(k in t for k in ["outfit", "fitcheck", "styling"]): return "Outfitcheck"
    if any(k in t for k in ["ugc", "home", "zuhause", "selfie"]): return "UGC / Zuhause"
    if any(k in t for k in ["shoot", "editorial", "kampagne", "lab_drop", "soul", "kling"]): return "Lifestyle-Shooting"
    if any(k in t for k in ["closeup", "detail", "flatlay", "color", "tee", "plunge", "capri", "loafer", "product"]): return "Produkt / Ästhetik"
    return "Sonstiges"

def lauf(befehl):
    return subprocess.run(befehl, check=True, capture_output=True)

def thumb_data(quelle, ist_bild):
    """200px breites Vorschaubild als eingebettete Daten — wie im Mac-Generator."""
    ziel = os.path.join(BASE, "_thumb_tmp.jpg")

    def versuch(befehl):
        if os.path.exists(ziel): os.remove(ziel)
        try:
            lauf(befehl)
        except subprocess.CalledProcessError:
            return False
        # Greift ffmpeg hinter das Ende des Clips, meldet es keinen Fehler, legt aber
        # nichts oder eine leere Datei an — deshalb hier die Groesse pruefen.
        return os.path.exists(ziel) and os.path.getsize(ziel) > 0

    grundriss = ["ffmpeg", "-y", "-loglevel", "error"]
    if ist_bild:
        ok = versuch(grundriss + ["-i", quelle, "-vf", "scale=200:-2", "-q:v", "6", ziel])
    else:
        ok = versuch(grundriss + ["-ss", "1", "-i", quelle, "-vframes", "1",
                                  "-vf", "scale=200:-2", "-q:v", "6", ziel])
        if not ok:
            # Sehr kurzer Clip: nochmal ganz am Anfang greifen, sonst bleibt die Karte leer.
            ok = versuch(grundriss + ["-ss", "0", "-i", quelle, "-vframes", "1",
                                      "-vf", "scale=200:-2", "-q:v", "6", ziel])
    if not ok:
        if os.path.exists(ziel): os.remove(ziel)
        return ""
    with open(ziel, "rb") as f:
        daten = base64.b64encode(f.read()).decode()
    os.remove(ziel)
    return "data:image/jpeg;base64," + daten

def verarbeiten():
    if not os.path.isdir(EINGANG):
        print("Kein eingang/ vorhanden — nichts zu tun.")
        return 0
    dateien = sorted(f for f in os.listdir(EINGANG)
                     if not f.startswith('.') and os.path.isfile(os.path.join(EINGANG, f)))
    if not dateien:
        print("eingang/ ist leer — nichts zu tun.")
        return 0

    with open(EINTRAEGE, encoding='utf-8') as f:
        bestand = json.load(f)
    vorhandene_ids = {e["id"] for e in bestand["eintraege"]}

    neu = 0
    offene_karten = {}   # Kennung -> Eintrag, um weitere Bilder derselben Karte anzuhaengen
    for name in dateien:
        quelle = os.path.join(EINGANG, name)
        sicher = saeubern(name)          # ab hier nur noch der gesaeuberte Name in Pfaden
        ist_bild = sicher.lower().endswith(BILD_EXT)
        ist_video = sicher.lower().endswith(VIDEO_EXT)
        if not ist_bild and not ist_video:
            if sicher.lower().endswith('.heic'):
                print(f"  Nicht uebernommen: {lesbar(sicher)} — das ist das iPhone-Fotoformat HEIC. "
                      "Bitte im Foto-Menue 'Kopieren und automatisch anpassen' waehlen oder als JPG hochladen.")
            else:
                print(f"  Nicht uebernommen: {lesbar(sicher)} — das ist weder ein Video noch ein Bild.")
            os.remove(quelle)
            continue

        if ist_bild:
            # Gehoeren mehrere Bilder zu einer Karte zum Durchswipen, hat der Dienst den
            # Kartennamen in den Dateinamen geschrieben — anders kann er nicht mitreisen,
            # weil jede Datei einzeln hochgeladen wird.
            kartenname, ohne_slot = slot_teile(sicher)
            # Ohne Kartennamen wird jedes Bild eine eigene Karte. Der Slot traegt dann den
            # vollen Namen samt Vorsatz, damit zwei gleich benannte Fotos nicht denselben
            # Slot (und damit dieselbe Notiz) erwischen.
            slot = kartenname or os.path.splitext(ohne_slot)[0]
            anzeige = kartenname or os.path.splitext(lesbar(ohne_slot))[0] or slot
            eintrag_id = f"INSPO_INBOX/bilder/{slot}"
            # Jedes Bild braucht innerhalb der Karte einen eigenen Dateinamen. Der Vorsatz
            # aus Zeitstempel und Zufall macht ihn eindeutig, auch bei gleichem Fotonamen.
            web_rel = f"web/INSPO_INBOX/bilder/{slot}/{os.path.splitext(ohne_slot)[0]}.jpg"
            ziel = os.path.join(BASE, web_rel)
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            try:
                lauf(["ffmpeg", "-y", "-loglevel", "error", "-i", quelle,
                      "-vf", "scale='min(1400,iw)':-2", "-q:v", "4", ziel])
            except subprocess.CalledProcessError as e:
                print(f"  Nicht uebernommen: {anzeige} — das Bild liess sich nicht verkleinern.")
                print(f"    (technische Meldung: {e.stderr.decode(errors='replace')[:200]})")
                # Halbfertiges Ergebnis und Quelle wegraeumen: sonst wandert eine kaputte
                # Datei ins Repository und dieselbe Quelle scheitert bei jedem Lauf erneut.
                if os.path.exists(ziel): os.remove(ziel)
                os.remove(quelle)
                continue
            thumb = thumb_data(quelle, True)
            # Zweites, drittes Bild derselben Karte: nur anhaengen, keine neue Karte.
            if eintrag_id in offene_karten:
                schon = offene_karten[eintrag_id]
                schon["bilder"].append({"src": web_rel, "thumb": thumb})
                schon["mb"] = round(schon["mb"] + os.path.getsize(ziel) / 1048576, 1)
                os.remove(quelle)
                neu += 1
                print(f"  Zur Karte „{anzeige}“ gelegt: Bild {len(schon['bilder'])}")
                continue
            eintrag = {"type": "bilder", "id": eintrag_id, "name": anzeige, "folder": "Bilder",
                       "src": "", "origin": "Inbox (neu)", "cat": guess(eintrag_id),
                       "cats": [guess(eintrag_id)], "notiz": "", "status": "",
                       "mb": round(os.path.getsize(ziel) / 1048576, 1), "date": "",
                       "quelle": "team",
                       "thumb": thumb, "bilder": [{"src": web_rel, "thumb": thumb}]}
        else:
            # Ausgabe immer als .mp4. Bei .mov waehlt ffmpeg sonst den QuickTime-Container,
            # GitHub Pages liefert video/quicktime aus und Firefox zeigt nur ein schwarzes Feld.
            datei = os.path.splitext(sicher)[0] + ".mp4"
            anzeige = lesbar(sicher)
            eintrag_id = f"INSPO_INBOX/videos/{datei}"
            web_rel = f"web/INSPO_INBOX/videos/{datei}"
            ziel = os.path.join(BASE, web_rel)
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            try:
                lauf(["ffmpeg", "-y", "-loglevel", "error", "-i", quelle,
                      "-vf", "scale=-2:720", "-c:v", "libx264", "-crf", "28", "-preset", "fast",
                      "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", ziel])
            except subprocess.CalledProcessError as e:
                print(f"  Nicht uebernommen: {anzeige} — das Video liess sich nicht umwandeln.")
                print(f"    (technische Meldung: {e.stderr.decode(errors='replace')[:200]})")
                if os.path.exists(ziel): os.remove(ziel)
                os.remove(quelle)
                continue
            eintrag = {"type": "video", "id": eintrag_id, "name": anzeige, "folder": "videos",
                       "src": web_rel, "origin": "Inbox (neu)", "cat": guess(eintrag_id),
                       "cats": [guess(eintrag_id)], "notiz": "", "status": "",
                       "mb": round(os.path.getsize(ziel) / 1048576, 1), "date": "",
                       "quelle": "team",
                       "thumb": thumb_data(quelle, False)}

        if eintrag_id in vorhandene_ids:
            print(f"  Ersetzt vorhandenen Eintrag: {anzeige}")
            bestand["eintraege"] = [e for e in bestand["eintraege"] if e["id"] != eintrag_id]
        bestand["eintraege"].insert(0, eintrag)   # neuestes zuerst, wie im Board
        vorhandene_ids.add(eintrag_id)
        if eintrag["type"] == "bilder":
            offene_karten[eintrag_id] = eintrag   # weitere Bilder landen in dieser Karte
        os.remove(quelle)
        neu += 1
        print(f"  Aufgenommen: {anzeige} ({eintrag['mb']} MB nach dem Verkleinern)")

    if neu:
        with open(EINTRAEGE, "w", encoding='utf-8') as f:
            json.dump(bestand, f, ensure_ascii=False)
    print(f"{neu} Datei(en) verarbeitet.")
    return neu

if __name__ == "__main__":
    sys.exit(0 if verarbeiten() >= 0 else 1)
