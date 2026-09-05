#!/usr/bin/env python3
"""Baut index.html neu — läuft auf GitHub, ohne Zugriff auf den Mac.

Zutaten (alle im Repository):
  eintraege.json   Liste aller Einträge inkl. Vorschaubilder und Web-Pfade
  BOARD_DATEN.json Themenliste, Zuordnungen, Notizen, Status, Ausgeblendetes
  .board_template.html  die Vorlage

Wird von der GitHub-Action bei jeder Datenänderung aufgerufen. Lokal macht das
weiterhin .build_board.py --web (das kann zusätzlich Videos verkleinern).

Team-Uploads können hier nicht verloren gehen: eintraege.json wird nur gelesen und nie
neu geschrieben. Zusammenführen muss nur der Mac, weil er die Liste aus INSPO_INBOX
komplett neu aufbaut — das macht .build_board.py.
"""
import json, os, re, datetime, sys

BASE = os.path.dirname(os.path.abspath(__file__))
# Alle Platzhalter, die .board_template.html enthalten darf — .build_board.py führt dieselbe
# Liste. Wer die Vorlage erweitert, muss beide ergänzen, sonst stünde der Platzhalter wörtlich
# auf der Seite. Unbekanntes bricht den Bau ab, statt es durchzulassen.
PLATZHALTER = {"__DATA__", "__CATS__", "__ORIGCHIPS__", "__N__", "__DATE__",
               "__MOBILE__", "__NURLESEN__", "__DIENST__", "__BAU__"}

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
def js(x):
    """JSON so einbetten, dass es den <script>-Block nicht sprengen kann.

    json.dumps laesst < > & unangetastet. Eine Notiz mit dem Text </script> wuerde
    das Skript-Element beenden — alles danach waere wieder HTML und koennte fremden
    Code auf die Seite bringen. Die Zeichen stehen in JSON immer innerhalb von
    Zeichenketten, deshalb ist die \\uXXXX-Schreibweise hier gefahrlos.
    U+2028/2029 sind in JSON erlaubt, in JavaScript-Zeichenketten aber Zeilenumbrueche.
    """
    return (json.dumps(x, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def h(s):
    """Text, der in ein HTML-Attribut oder zwischen Tags geht."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


bau = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

with open(os.path.join(BASE, ".board_template.html"), encoding='utf-8') as f:
    out = f.read()
unbekannt = sorted(set(re.findall(r"__[A-Z0-9_]+__", out)) - PLATZHALTER)
if unbekannt:
    sys.exit("In der Vorlage steht etwas Neues: " + ", ".join(unbekannt)
             + " — render_web.py kennt es noch nicht, die Seite wurde nicht gebaut.")
out = out.replace("__DATA__", js(sichtbar))
out = out.replace("__CATS__", js(CATS))
out = out.replace("__ORIGCHIPS__", "".join(
    f'<span class="chip of" data-o="{h(o)}">{h(o)}</span>' for o in origins))
out = out.replace("__N__", str(len(sichtbar)))
out = out.replace("__DATE__", datetime.date.today().strftime("%d.%m.%Y"))
out = out.replace("__MOBILE__", "false")
out = out.replace("__NURLESEN__", "true")
out = out.replace("__DIENST__", "https://caliante-board-dienst.myaffiliate24.workers.dev")
out = out.replace("__BAU__", bau)

with open(os.path.join(BASE, "index.html"), "w", encoding='utf-8') as f:
    f.write(out)
with open(os.path.join(BASE, "version.txt"), "w", encoding='utf-8') as f:
    f.write(bau)

print(f"index.html neu gebaut: {len(sichtbar)} Einträge, {len(CATS)} Themen, Stand {bau}")
