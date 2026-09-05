#!/bin/bash
# Doppelklick: setzt das Team-Passwort fuer die Online-Seite neu.
#
# Das alte Passwort kann niemand auslesen — Cloudflare gibt hinterlegte Geheimnisse
# grundsaetzlich nicht mehr heraus. Wenn es keiner mehr weiss, setzt man ein neues.
cd "$(dirname "$0")"
echo ""
echo "  CALIANTÉ — Team-Passwort setzen"
echo "  ==============================="
echo ""
echo "  Damit melden sich du und dein Team auf der Online-Seite an,"
echo "  um Themen und Notizen zu aendern."
echo ""
echo "  Hinweis: Wer gerade angemeldet ist, muss sich danach neu anmelden."
echo ""

# ---------- Neues Passwort erfragen ----------
while true; do
  echo -n "  Neues Passwort (mind. 8 Zeichen): "
  read -r -s PW1
  echo ""

  if [ ${#PW1} -lt 8 ]; then
    echo "  Zu kurz — bitte mindestens 8 Zeichen."
    echo ""
    continue
  fi

  echo -n "  Zur Sicherheit nochmal:           "
  read -r -s PW2
  echo ""

  if [ "$PW1" != "$PW2" ]; then
    echo "  Die beiden stimmen nicht ueberein. Nochmal."
    echo ""
    continue
  fi
  break
done

# ---------- Bei Cloudflare hinterlegen ----------
echo ""
echo "  Hinterlege es beim Online-Dienst …"
if ! printf '%s' "$PW1" | (cd board-dienst && npx --yes wrangler secret put BOARD_PASSWORT >/dev/null 2>&1); then
  echo ""
  echo "  Hat nicht geklappt. Sag Claude Bescheid und nenne diesen Punkt:"
  echo "  'Passwort setzen abgelehnt'."
  echo ""
  read -n 1 -s -r -p "  (Taste zum Schliessen)"
  exit 1
fi
echo "  Hinterlegt."

# ---------- Echt gegen den laufenden Dienst pruefen ----------
echo ""
echo "  Teste es gegen die echte Seite …"
sleep 3   # der Dienst braucht einen Moment, bis das neue Geheimnis greift

ANTWORT=$(curl -s -X POST https://caliante-board-dienst.myaffiliate24.workers.dev/anmelden \
  -H "Content-Type: application/json" \
  --data-binary "$(printf '%s' "$PW1" | python3 -c 'import json,sys; print(json.dumps({"passwort": sys.stdin.read()}))')")

if printf '%s' "$ANTWORT" | grep -q '"ok":true'; then
  echo "  Test bestanden — die Anmeldung funktioniert."
  echo ""
  echo "  ==============================="
  echo "  Fertig. Merk dir das Passwort gut."
  echo ""
  echo "  Deine Team-Seite:"
  echo "  https://mantyga777-coder.github.io/caliante-inspo-board/"
  echo ""
else
  echo ""
  echo "  Das Passwort ist hinterlegt, aber der Test schlug fehl."
  echo "  Antwort des Dienstes:"
  echo "  $ANTWORT"
  echo ""
  echo "  Sag Claude Bescheid und zeig ihm diese Zeile."
  echo ""
fi

read -n 1 -s -r -p "  (Taste zum Schliessen)"
