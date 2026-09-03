#!/bin/bash
# Doppelklick: baut das Board neu und schickt den aktuellen Stand ans Team.
cd "$(dirname "$0")"
echo ""
echo "  CALIANTÉ — Board wird veröffentlicht …"
echo ""

python3 .build_board.py || { echo "  Bauen fehlgeschlagen."; read -n 1 -s -r -p "  (Taste zum Schließen)"; exit 1; }

# Die eigenständige Fassung ist das, was das Team im Browser sieht.
cp CALIANTE_BOARD_HANDY.html index.html

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
