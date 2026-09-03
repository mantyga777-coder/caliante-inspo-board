#!/bin/bash
# Doppelklick auf diese Datei baut das Board neu.
cd "$(dirname "$0")"
echo ""
echo "  CALIANTÉ — Board wird aktualisiert …"
echo ""
python3 .build_board.py
echo ""
echo "  Fertig. Du kannst dieses Fenster schließen."
echo "  Öffne CALIANTE_VIDEO_BOARD.html per Doppelklick."
echo ""
read -n 1 -s -r -p "  (beliebige Taste zum Schließen)"
