#!/bin/bash
# Doppelklick: bringt die GitHub-Anmeldung in Ordnung und hinterlegt denselben
# Schluessel im Cloudflare-Dienst, damit das Team online speichern kann.
#
# Ein Schluessel fuer beides. Frueher lief Teil 1 ueber den Browser mit einem
# Einmal-Code — daran ist es gescheitert, weil das Fenster zwischendurch auf eine
# Taste wartete und niemand wusste, worauf. Jetzt: einmal einfuegen, fertig.
cd "$(dirname "$0")"
echo ""
echo "  CALIANTÉ — Zugang einrichten"
echo "  ============================"
echo ""

# ---------- Steht schon alles? ----------
GH_OK=0; CF_OK=0
gh auth status >/dev/null 2>&1 && GH_OK=1
(cd board-dienst && npx --yes wrangler secret list 2>/dev/null | grep -q GH_TOKEN) && CF_OK=1

if [ "$GH_OK" = 1 ] && [ "$CF_OK" = 1 ]; then
  echo "  Alles ist bereits eingerichtet — nichts zu tun."
  echo ""
  read -n 1 -s -r -p "  (Taste zum Schliessen)"
  exit 0
fi

echo "  Noch offen:"
[ "$GH_OK" = 0 ] && echo "    - die Anmeldung auf diesem Mac"
[ "$CF_OK" = 0 ] && echo "    - der Schluessel fuer den Online-Dienst"
echo ""
echo "  Beides wird mit EINEM Schluessel erledigt."
echo ""

cat <<'ANLEITUNG'
  ------------------------------------------------------------------
  SO BEKOMMST DU DEN SCHLUESSEL  (dauert 2 Minuten)

   1. Diese Seite im Browser oeffnen:

      https://github.com/settings/personal-access-tokens/new

   2. Ausfuellen:

      Token name         ->  Caliante Board
      Expiration         ->  No expiration
      Repository access  ->  Only select repositories
                             und darunter  caliante-inspo-board  auswaehlen

   3. Weiter unten bei "Permissions" den Abschnitt
      "Repository permissions" aufklappen und suchen:

      Contents           ->  auf  Read and write  stellen

   4. Ganz unten auf  "Generate token"  klicken.
      Danach erscheint ein langer Text, der mit  github_pat_  anfaengt.
      Diesen kopieren (er wird nur ein einziges Mal angezeigt).
  ------------------------------------------------------------------

ANLEITUNG

echo -n "  Schluessel hier einfuegen und Enter druecken: "
read -r -s GHTOKEN
echo ""

if [ -z "$GHTOKEN" ]; then
  echo ""
  echo "  Nichts eingegeben — abgebrochen. Einfach nochmal doppelklicken."
  echo ""
  read -n 1 -s -r -p "  (Taste zum Schliessen)"
  exit 1
fi

# ---------- Schluessel pruefen, bevor irgendwas damit gemacht wird ----------
echo ""
echo "  Pruefe den Schluessel …"
PRUEF=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $GHTOKEN" \
  https://api.github.com/repos/mantyga777-coder/caliante-inspo-board)

if [ "$PRUEF" != "200" ]; then
  echo ""
  echo "  Der Schluessel funktioniert nicht (Antwort $PRUEF)."
  case "$PRUEF" in
    401) echo "  Das heisst: der Text stimmt nicht. Beim Kopieren vielleicht" ;
         echo "  etwas abgeschnitten? Er muss mit  github_pat_  anfangen." ;;
    404) echo "  Das heisst: der Schluessel darf nicht auf dieses Projekt zugreifen." ;
         echo "  Bei 'Repository access' muss  caliante-inspo-board  ausgewaehlt sein." ;;
    *)   echo "  Bitte pruefen, ob 'Contents: Read and write' gesetzt war." ;;
  esac
  echo ""
  read -n 1 -s -r -p "  (Taste zum Schliessen)"
  exit 1
fi
echo "  Schluessel ist gueltig."

# ---------- Teil 1: Anmeldung auf diesem Mac ----------
echo ""
echo "  [1 von 2] Anmeldung auf diesem Mac …"
if [ "$GH_OK" = 1 ]; then
  echo "  War schon in Ordnung."
else
  gh auth logout --hostname github.com >/dev/null 2>&1   # alten, ungueltigen Eintrag raeumen
  if printf '%s' "$GHTOKEN" | gh auth login --hostname github.com --git-protocol https --with-token 2>/dev/null \
     && gh auth status >/dev/null 2>&1; then
    echo "  Erledigt — Veroeffentlichen geht wieder."
  else
    echo ""
    echo "  Die Anmeldung wurde nicht angenommen."
    echo "  Sag Claude Bescheid und nenne diesen Punkt: 'Teil 1 abgelehnt'."
    echo ""
    read -n 1 -s -r -p "  (Taste zum Schliessen)"
    exit 1
  fi
fi

# ---------- Teil 2: derselbe Schluessel fuer den Online-Dienst ----------
echo ""
echo "  [2 von 2] Schluessel fuer den Online-Dienst hinterlegen …"
if printf '%s' "$GHTOKEN" | (cd board-dienst && npx --yes wrangler secret put GH_TOKEN >/dev/null 2>&1); then
  echo "  Erledigt — das Team kann online speichern."
else
  echo ""
  echo "  Konnte den Schluessel nicht bei Cloudflare hinterlegen."
  echo "  Teil 1 hat aber geklappt. Sag Claude Bescheid und nenne diesen"
  echo "  Punkt: 'Teil 2 abgelehnt'."
  echo ""
  read -n 1 -s -r -p "  (Taste zum Schliessen)"
  exit 1
fi

echo ""
echo "  ============================"
echo "  Alles eingerichtet."
echo ""
echo "  Sag Claude jetzt Bescheid. Nicht selbst veroeffentlichen —"
echo "  er prueft vorher, ob wirklich alles stimmt."
echo ""
read -n 1 -s -r -p "  (Taste zum Schliessen)"
