#!/usr/bin/env python3
"""Verarbeitet neu hochgeladene Dateien aus eingang/ — laeuft auf GitHub.

Fuer jede Datei: verkleinerte Web-Fassung erzeugen, Vorschaubild bauen, Eintrag in
eintraege.json aufnehmen, Original aus eingang/ entfernen. Danach baut render_web.py
die Seite neu. Ergibt dieselben Eintraege wie .build_board.py auf dem Mac.
"""
import base64, hashlib, json, os, subprocess, sys, time

BASE = os.path.dirname(os.path.abspath(__file__))
EINGANG = os.path.join(BASE, "eingang")
WEB = os.path.join(BASE, "web", "INSPO_INBOX")
EINTRAEGE = os.path.join(BASE, "eintraege.json")
VIDEO_EXT = ('.mp4', '.mov', '.webm', '.m4v')
BILD_EXT = ('.jpg', '.jpeg', '.png', '.heic', '.webp')

def guess(t):
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
    try:
        if ist_bild:
            lauf(["ffmpeg", "-y", "-loglevel", "error", "-i", quelle,
                  "-vf", "scale=200:-2", "-q:v", "6", ziel])
        else:
            lauf(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", quelle,
                  "-vframes", "1", "-vf", "scale=200:-2", "-q:v", "6", ziel])
    except subprocess.CalledProcessError:
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
    for name in dateien:
        quelle = os.path.join(EINGANG, name)
        ist_bild = name.lower().endswith(BILD_EXT)
        ist_video = name.lower().endswith(VIDEO_EXT)
        if not ist_bild and not ist_video:
            print(f"  Uebersprungen (kein Video/Bild): {name}")
            os.remove(quelle)
            continue

        if ist_bild:
            # Bilder werden zu einem eigenen Slot mit einem Bild — wie beim Mac-Upload.
            slot = os.path.splitext(name)[0]
            eintrag_id = f"INSPO_INBOX/bilder/{slot}"
            web_rel = f"web/INSPO_INBOX/bilder/{slot}/{os.path.splitext(name)[0]}.jpg"
            ziel = os.path.join(BASE, web_rel)
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            try:
                lauf(["ffmpeg", "-y", "-loglevel", "error", "-i", quelle,
                      "-vf", "scale='min(1400,iw)':-2", "-q:v", "4", ziel])
            except subprocess.CalledProcessError as e:
                print(f"  FEHLER beim Verkleinern von {name}: {e.stderr.decode()[:200]}")
                continue
            thumb = thumb_data(quelle, True)
            eintrag = {"type": "bilder", "id": eintrag_id, "name": slot, "folder": "Bilder",
                       "src": "", "origin": "Inbox (neu)", "cat": guess(eintrag_id),
                       "cats": [guess(eintrag_id)], "notiz": "", "status": "",
                       "mb": round(os.path.getsize(ziel) / 1048576, 1), "date": "",
                       "thumb": thumb, "bilder": [{"src": web_rel, "thumb": thumb}]}
        else:
            eintrag_id = f"INSPO_INBOX/videos/{name}"
            web_rel = f"web/INSPO_INBOX/videos/{name}"
            ziel = os.path.join(BASE, web_rel)
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            try:
                lauf(["ffmpeg", "-y", "-loglevel", "error", "-i", quelle,
                      "-vf", "scale=-2:720", "-c:v", "libx264", "-crf", "28", "-preset", "fast",
                      "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", ziel])
            except subprocess.CalledProcessError as e:
                print(f"  FEHLER beim Verkleinern von {name}: {e.stderr.decode()[:200]}")
                continue
            eintrag = {"type": "video", "id": eintrag_id, "name": name, "folder": "videos",
                       "src": web_rel, "origin": "Inbox (neu)", "cat": guess(eintrag_id),
                       "cats": [guess(eintrag_id)], "notiz": "", "status": "",
                       "mb": round(os.path.getsize(ziel) / 1048576, 1), "date": "",
                       "thumb": thumb_data(quelle, False)}

        if eintrag_id in vorhandene_ids:
            print(f"  Ersetzt vorhandenen Eintrag: {name}")
            bestand["eintraege"] = [e for e in bestand["eintraege"] if e["id"] != eintrag_id]
        bestand["eintraege"].insert(0, eintrag)   # neuestes zuerst, wie im Board
        vorhandene_ids.add(eintrag_id)
        os.remove(quelle)
        neu += 1
        print(f"  Aufgenommen: {name} ({eintrag['mb']} MB nach dem Verkleinern)")

    if neu:
        with open(EINTRAEGE, "w", encoding='utf-8') as f:
            json.dump(bestand, f, ensure_ascii=False)
    print(f"{neu} Datei(en) verarbeitet.")
    return neu

if __name__ == "__main__":
    sys.exit(0 if verarbeiten() >= 0 else 1)
