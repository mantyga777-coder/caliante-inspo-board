#!/usr/bin/env python3
"""Baut index.html neu — läuft auf GitHub, ohne Zugriff auf den Mac.

Zutaten (alle im Repository):
  eintraege.json   Liste aller Einträge inkl. Vorschaubilder und Web-Pfade
  BOARD_DATEN.json Themenliste, Zuordnungen, Notizen, Status, Ausgeblendetes
  .board_template.html  die Vorlage

Wird von der GitHub-Action bei jeder Datenänderung aufgerufen. Lokal macht das
weiterhin .build_board.py --web (das kann zusätzlich Videos verkleinern).
"""
import json, os, datetime, sys

BASE = os.path.dirname(os.path.abspath(__file__))

def laden(name):
    with open(os.path.join(BASE, name), encoding='utf-8') as f:
        return json.load(f)

eintraege_datei = laden("eintraege.json")
eintraege = eintraege_datei["eintraege"]
daten = laden("BOARD_DATEN.json")
CATS = [k for k in daten.get("kategorien", []) if str(k).strip()] or eintraege_datei["kategorien"]
NOTFALL = "Sonstiges" if "Sonstiges" in CATS else CATS[-1]
gespeichert = daten.get("eintraege", {})

sichtbar = []
for e in eintraege:
    s = gespeichert.get(e["id"], {})
    if s.get("ausgeblendet"):
        continue                      # Ausgeblendetes gehört nicht auf die Team-Seite
    kats = s.get("kategorien")
    if kats is None:
        alt = s.get("kategorie")      # altes Format: eine einzelne Kategorie
        kats = [alt] if alt else e.get("cats") or [e.get("cat")]
    kats = [k for k in kats if k in CATS] or [NOTFALL]
    e = dict(e)
    e["cats"] = kats
    e["cat"] = kats[0]
    e["notiz"] = s.get("notiz", "")
    e["status"] = s.get("status", "")
    e.pop("aus", None)
    sichtbar.append(e)

origins = ["Inbox (neu)", "Referenz", "Eigenes Material"]
bau = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

with open(os.path.join(BASE, ".board_template.html"), encoding='utf-8') as f:
    out = f.read()
out = out.replace("__DATA__", json.dumps(sichtbar, ensure_ascii=False))
out = out.replace("__CATS__", json.dumps(CATS, ensure_ascii=False))
out = out.replace("__ORIGCHIPS__", "".join(
    f'<span class="chip of" data-o="{o}">{o}</span>' for o in origins))
out = out.replace("__N__", str(len(sichtbar)))
out = out.replace("__DATE__", datetime.date.today().strftime("%d.%m.%Y"))
out = out.replace("__MOBILE__", "false")
out = out.replace("__NURLESEN__", "true")
out = out.replace("__BAU__", bau)

with open(os.path.join(BASE, "index.html"), "w", encoding='utf-8') as f:
    f.write(out)
with open(os.path.join(BASE, "version.txt"), "w", encoding='utf-8') as f:
    f.write(bau)

print(f"index.html neu gebaut: {len(sichtbar)} Einträge, {len(CATS)} Themen, Stand {bau}")
