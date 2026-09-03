#!/bin/bash
# Doppelklick: baut das Board neu und schickt den aktuellen Stand ans Team.
cd "$(dirname "$0")"
echo ""
echo "  CALIANTÉ — Board wird veröffentlicht …"
echo ""

# Erst holen, was online geändert wurde (z.B. von Felix), sonst überschreibt dieser
# Rechner seine Arbeit. Bei einem Konflikt lieber abbrechen als etwas zerstören.
if ! git pull --rebase --autostash -q 2>/dev/null; then
  git rebase --abort 2>/dev/null
  echo "  Achtung: Online gibt es Änderungen, die sich nicht automatisch"
  echo "  mit deinen zusammenführen lassen. Nichts wurde hochgeladen."
  echo "  Sag Claude Bescheid, dann löse ich das auf."
  echo ""
  read -n 1 -s -r -p "  (Taste zum Schließen)"
  exit 1
fi

# --web ist entscheidend: erzeugt index.html mit den verkleinerten, abspielbaren Videos.
# Ohne den Schalter hätte die Team-Seite nur Standbilder.
python3 .build_board.py --web || { echo "  Bauen fehlgeschlagen."; read -n 1 -s -r -p "  (Taste zum Schließen)"; exit 1; }

# Sicherheitsnetz: nicht hochladen, wenn die Videos in der Team-Fassung nicht abspielbar wären.
python3 - <<'PRUEFUNG' || { echo ""; echo "  Abgebrochen — nichts hochgeladen."; read -n 1 -s -r -p "  (Taste zum Schließen)"; exit 1; }
import re, json, sys
h = open("index.html", encoding="utf-8").read()
d = json.loads(re.search(r"const DATA=(\[.*?\]), CATS=", h, re.S).group(1))
videos = [v for v in d if v["type"] == "video"]
ohne = [v for v in videos if not v.get("src")]
if videos and ohne:
    print(f"  ! {len(ohne)} von {len(videos)} Videos hätten keinen abspielbaren Pfad.")
    sys.exit(1)
if "NURLESEN=true" not in h:
    print("  ! index.html ist nicht im Nur-Lesen-Modus — Team würde tote Knöpfe sehen.")
    sys.exit(1)
print(f"  Prüfung ok: {len(videos)} Videos abspielbar, Nur-Lesen-Modus aktiv.")
PRUEFUNG

if [ -z "$(git status --porcelain)" ]; then   # --porcelain sieht auch neue Dateien, git diff nicht
  echo ""
  echo "  Keine Änderungen seit der letzten Veröffentlichung."
  echo ""
  read -n 1 -s -r -p "  (Taste zum Schließen)"
  exit 0
fi

git add -A
git commit -q -m "Board-Stand vom $(date '+%d.%m.%Y %H:%M')"
if git push -q origin HEAD 2>&1; then
  echo ""
  echo "  Fertig. Dein Team sieht den neuen Stand in etwa einer Minute."
else
  echo ""
  echo "  Hochladen fehlgeschlagen — Internetverbindung prüfen."
fi
echo ""
read -n 1 -s -r -p "  (Taste zum Schließen)"
