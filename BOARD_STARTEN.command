#!/bin/bash
# Doppelklick auf diese Datei startet das Board zum Bearbeiten.
cd "$(dirname "$0")"
echo ""
echo "  CALIANTÉ — Board wird gestartet …"
python3 .board_server.py
