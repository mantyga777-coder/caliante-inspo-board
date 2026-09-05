#!/bin/bash
# Doppelklick: bringt die GitHub-Anmeldung in Ordnung und hinterlegt den
# Schluessel im Cloudflare-Dienst, damit das Team online speichern kann.
cd "$(dirname "$0")"
echo ""
echo "  CALIANTÉ — Zugang einrichten"
echo "  ============================"
echo ""

# ---------- Teil 1: GitHub-Anmeldung auf diesem Mac ----------
echo "  [1 von 2] GitHub-Anmeldung auf diesem Mac"
echo ""
if gh auth status >/dev/null 2>&1; then
  echo "  Anmeldung ist gueltig — nichts zu tun."
else
  echo "  Die Anmeldung fehlt oder ist abgelaufen."
  echo "  Gleich oeffnet sich dein Browser. Dort bestaetigen, dann hierher zurueck."
  echo ""
  read -n 1 -s -r -p "  (beliebige Taste zum Starten)"
  echo ""
  echo ""
  if gh auth login --hostname github.com --git-protocol https --web; then
    echo ""
    echo "  Anmeldung erfolgreich."
  else
    echo ""
    echo "  Anmeldung abgebrochen. Ohne sie kannst du nicht veroeffentlichen."
    read -n 1 -s -r -p "  (Taste zum Schliessen)"
    exit 1
  fi
fi

# ---------- Teil 2: Schluessel fuer den Online-Dienst ----------
echo ""
echo "  [2 von 2] Schluessel fuer den Online-Dienst"
echo ""
if (cd board-dienst && npx --yes wrangler secret list 2>/dev/null | grep -q GH_TOKEN); then
  echo "  Schluessel ist bereits hinterlegt."
  echo -n "  Neu setzen? (j/n) "
  read -r antwort
  [ "$antwort" != "j" ] && { echo ""; echo "  Alles erledigt."; read -n 1 -s -r -p "  (Taste zum Schliessen)"; exit 0; }
fi

cat <<'ANLEITUNG'

  Du brauchst einen GitHub-Schluessel, der NUR dieses eine Projekt bearbeiten darf.
  Er wird geheim bei Cloudflare hinterlegt und ist fuer niemanden sichtbar.

  So bekommst du ihn (dauert 2 Minuten):

   1. Diese Seite oeffnen:
      https://github.com/settings/personal-access-tokens/new

   2. Ausfuellen:
      Token name          -> Caliante Board
      Expiration          -> No expiration  (sonst hoert es irgendwann auf zu gehen)
      Repository access   -> Only select repositories
                             -> caliante-inspo-board auswaehlen
      Permissions -> Repository permissions -> Contents -> Read and write

   3. Unten auf "Generate token", dann den Schluessel kopieren
      (er beginnt mit  github_pat_  und wird nur einmal angezeigt)

ANLEITUNG

echo -n "  Schluessel hier einfuegen und Enter druecken: "
read -r -s GHTOKEN
echo ""

if [ -z "$GHTOKEN" ]; then
  echo "  Nichts eingegeben — abgebrochen."
  read -n 1 -s -r -p "  (Taste zum Schliessen)"
  exit 1
fi

echo ""
echo "  Pruefe den Schluessel …"
PRUEF=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $GHTOKEN" \
  https://api.github.com/repos/mantyga777-coder/caliante-inspo-board)
if [ "$PRUEF" != "200" ]; then
  echo "  Der Schluessel funktioniert nicht (Antwort $PRUEF)."
  echo "  Bitte pruefen, ob das richtige Projekt und 'Contents: Read and write' gewaehlt war."
  read -n 1 -s -r -p "  (Taste zum Schliessen)"
  exit 1
fi
echo "  Schluessel ist gueltig."

echo ""
echo "  Hinterlege ihn im Online-Dienst …"
if printf '%s' "$GHTOKEN" | (cd board-dienst && npx --yes wrangler secret put GH_TOKEN >/dev/null 2>&1); then
  echo "  Fertig — das Team kann jetzt online speichern."
else
  echo "  Konnte den Schluessel nicht hinterlegen."
  echo "  Sag Claude Bescheid, dann schaue ich es mir an."
  read -n 1 -s -r -p "  (Taste zum Schliessen)"
  exit 1
fi

echo ""
echo "  Alles eingerichtet. Jetzt einmal BOARD_VEROEFFENTLICHEN.command"
echo "  doppelklicken, damit die neue Fassung online geht."
echo ""
read -n 1 -s -r -p "  (Taste zum Schliessen)"
