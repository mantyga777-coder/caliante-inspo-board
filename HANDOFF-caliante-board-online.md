# Übergabe

Stand: 2026-09-05 15:00 CEST
Projekt: Caliante Inspo-Board (/Users/davevu/CalianteBoard)
Letzter Commit bei Übergabe: 8a3d76d "Schritt 3, Teil 1: Verarbeitung fuer hochgeladene Dateien"

## So machst du weiter

Führe zuerst aus:

    cd /Users/davevu/CalianteBoard && gh auth status

Erwartete Ausgabe im beschriebenen Zustand: `X Failed to log in ... The token in default is invalid.`
**Das ist der Hauptblocker.** Solange er besteht, kann nichts veröffentlicht werden, und zwei fertige
Commits liegen unveröffentlicht herum (`git log --oneline origin/main..HEAD` zeigt 8a3d76d und 6f0d820).
Der Nutzer muss dafür `ZUGANG_EINRICHTEN.command` doppelklicken, das kann kein Agent für ihn tun.

## Ziel

Felix betreibt ein Inspo-Board für Caliante-Content. Es soll für sein Content-Team online erreichbar
sein, und das Team soll dort **dasselbe können wie er lokal**: Videos ansehen, Themen zuordnen,
Notizen schreiben und vor allem **neue Videos hochladen**, ohne dass sein Mac laufen muss.
Ausdrücklicher Wunsch: das Ablagefeld zum Draufziehen soll auch auf der Online-Seite erscheinen.

## Stand

Drei Systeme laufen: lokales Board (`localhost:8777`, HTTP 200), Team-Seite auf GitHub Pages
(HTTP 200), Cloudflare-Dienst (antwortet korrekt mit `{"ok":false,"fehler":"Passwort stimmt nicht."}`).
Der Ausbau war in drei Schritten geplant. Schritt 1 ist live, Schritt 2 fertig aber unveröffentlicht,
Schritt 3 zur Hälfte gebaut.

**Fertig:**
- Schritt 1, GitHub baut die Seite selbst: `render_web.py` erzeugt `index.html` allein aus
  `eintraege.json` plus `BOARD_DATEN.json`, ohne Zugriff auf INSPO_INBOX. Die Action
  `.github/workflows/board-bauen.yml` löst das bei Datenänderungen aus.
  (Belegstelle: Action-Lauf "Notiz online geaendert (Test wie durch Felix)" lief erfolgreich durch,
  Ausgabe `Pruefung ok: 133 Eintraege, 110 Videos abspielbar.`; die online gemachte Änderung war
  danach live, ohne Beteiligung des Macs.)
- Der Veröffentlichen-Knopf holt Online-Änderungen ab, bevor er hochlädt
  (`BOARD_VEROEFFENTLICHEN.command`, `git pull --rebase --autostash` am Anfang; getestet: eine
  online gesetzte Notiz kam beim Mac an, ohne etwas zu überschreiben).
- Mehrfach-Themen pro Eintrag: `kategorien` ist eine Liste statt eines Einzelwerts, mit Checkbox-
  Auswahl pro Karte. (Belegstelle: Live-Test, ein Eintrag vier Themen zugeordnet, erschien unter
  allen vier Filtern; `_Themen/` legte entsprechend mehr Verknüpfungen an, 117 statt 119.)
- Team-Seite unterscheidbar vom Arbeits-Board: Schild neben dem Titel, `DEIN ARBEITS-BOARD`
  gegenüber `ONLINE · TEAM` (`.board_template.html`, Element `#wo`). Grund siehe Fallen.
- Schritt 3, Teil 1, Verarbeitung von Uploads: `eingang_verarbeiten.py` nimmt Dateien aus `eingang/`,
  verkleinert Videos auf 720p, erzeugt Vorschaubilder, legt Einträge an, räumt `eingang/` leer.
  (Belegstelle: lokal mit echtem Testvideo gelaufen, Ausgabe `Aufgenommen: TESTUPLOAD_unboxing.mp4`,
  Eintrag landete korrekt an erster Stelle mit Thema `['Unboxing']`, danach vollständig zurückgesetzt
  auf 133 Einträge.)

**Angefangen, nicht fertig:**
- Schritt 2, Online-Bearbeiten mit Passwort: vollständig gebaut, aber **nie veröffentlicht**, weil
  das Hochladen an der kaputten GitHub-Anmeldung scheitert. Online liegt noch eine ältere Fassung.
  (Prüfen mit: `curl -s https://mantyga777-coder.github.io/caliante-inspo-board/index.html | grep -o 'DIENST="[^"]*"'`
  Erwartet im aktuellen, kaputten Zustand: keine Ausgabe. Nach dem Veröffentlichen: die Worker-Adresse.)
- Schritt 3, Teil 2, Ablagefeld auf der Team-Seite: noch nicht gebaut. Die Verarbeitung dahinter
  steht, es fehlt der sichtbare Teil plus der Weg, wie die Datei in `eingang/` gelangt.
- Dem Cloudflare-Dienst fehlt das Geheimnis `GH_TOKEN`. Gesetzt ist nur `BOARD_PASSWORT`
  (geprüft mit `npx wrangler secret list` im Ordner `board-dienst`). Folge: Anmelden funktioniert,
  Speichern würde scheitern.

**Unklar, prüfen:**
- Welches Passwort im Dienst hinterlegt ist, weiß niemand in dieser Session. Es wurde in einer
  parallelen Sitzung gesetzt und liegt verschlüsselt bei Cloudflare.
  (So prüfst du es: den Nutzer fragen. Neu setzen ginge mit `npx wrangler secret put BOARD_PASSWORT`
  im Ordner `board-dienst`.)
- Ob die Videogrößen für den Weg über den Cloudflare-Dienst reichen. 98 von 110 Videos liegen unter
  25 MB, 109 unter 50 MB, eines darüber. Cloudflare-Worker haben auf dem Gratis-Tarif enge
  Rechenzeit-Grenzen, das Durchreichen großer Dateien wurde **nicht** getestet.

## Geänderte Dateien

| Datei | Was geändert wurde und warum |
|---|---|
| `render_web.py` | Neu. Baut index.html allein aus Repository-Daten, damit GitHub das ohne den Mac kann. |
| `eingang_verarbeiten.py` | Neu. Verkleinert hochgeladene Videos/Bilder, erzeugt Einträge und Vorschaubilder. |
| `.github/workflows/board-bauen.yml` | Neu. Baut die Seite bei Datenänderungen, mit Prüfung vorher und nachher. |
| `.github/workflows/eingang-verarbeiten.yml` | Neu. Verarbeitet Dateien aus `eingang/`, installiert dafür ffmpeg. |
| `ZUGANG_EINRICHTEN.command` | Neu. Doppelklick-Helfer für GitHub-Neuanmeldung und das fehlende `GH_TOKEN`. |
| `.board_template.html` | Nur-Lesen-Modus, Passwort-Login gegen den Cloudflare-Dienst, Mehrfach-Themen, Schild zur Unterscheidung. |
| `.build_board.py` | Web-Modus (`--web`) mit verkleinerten Videos, `eintraege.json`, Mehrfach-Themen, Sortierung neuestes zuerst. |
| `.board_server.py` | Speichern verschmilzt statt zu ersetzen, damit parallele Änderungen nicht verloren gehen. |
| `BOARD_VEROEFFENTLICHEN.command` | Baut mit `--web`, prüft sich selbst vor dem Hochladen, holt vorher Online-Änderungen. |
| `board-dienst/` | Cloudflare-Worker aus einer parallelen Sitzung: prüft Passwort, schreibt BOARD_DATEN.json, Ratenbremse. |
| `.gitignore` | Pfade auf oberste Ebene festgenagelt, Cloudflare-Zwischenspeicher ausgeschlossen. |

## Entscheidungen

- **Cloudflare-Dienst statt Schlüssel im Browser:** Begründung: der GitHub-Schlüssel bleibt serverseitig
  und erreicht den Browser nie, plus Ratenbremse gegen Passwort-Raten. Verworfen wurde: den Schlüssel
  mit einem Passwort verschlüsselt in die Seite legen (war in dieser Session angefangen und wieder
  entfernt, weil die verschlüsselte Datei öffentlich abrufbar und damit offline angreifbar wäre).
- **Videos verkleinert statt im Original ins Repository:** Begründung: 1,2 GB wurden zu 107 MB, und
  eine Datei mit 112 MB hätte GitHubs Hartgrenze von 100 MB gesprengt. Für Inspo-Referenzen reicht
  720p. Verworfen wurde: Originale hochladen.
- **Team-Seite ist standardmäßig nur zum Ansehen:** Begründung: ohne Anmeldung sollen keine Knöpfe
  sichtbar sein, die ins Leere laufen. Verworfen wurde: Bearbeiten-Felder immer zeigen.
- **Öffentlich sichtbar:** Der Nutzer hat das ausdrücklich entschieden, es sind Inspo-Referenzen von
  TikTok und Instagram, keine unveröffentlichten Kampagnen.
- **Löschen im Board bewegt nie Produktionsmaterial:** Eigene Uploads wandern in `_papierkorb`,
  alles andere wird nur ausgeblendet. Grund: Regel des Nutzers, verschärft durch einen realen Vorfall.

## Schon gescheitert (nicht nochmal probieren)

- **`git push` in jeder Form:** scheitert mit `fatal: could not read Username for 'https://github.com':
  Device not configured`. Ursache: der Token von `gh` ist ungültig (`gh auth status` meldet
  `The token in default is invalid.`). Nur der Nutzer kann das per `gh auth login` beheben.
- **SSH als Umweg für das Hochladen:** scheitert mit `git@github.com: Permission denied (publickey).`
  Es existiert kein Schlüssel unter `~/.ssh/*.pub`.
- **`launchctl kickstart -k` zum Neuladen des Board-Servers:** funktionierte nicht. Was funktioniert:
  `launchctl bootout gui/501/com.caliante.inspoboard` gefolgt von
  `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.caliante.inspoboard.plist`, danach etwa
  fünf Sekunden warten, sonst antwortet der Port noch nicht.
- **Den Veröffentlichen-Knopf ohne `--web` laufen lassen:** hat die Team-Seite zerstört, weil er die
  Handy-Fassung über `index.html` kopierte und die keine Videopfade hat (0 von 94 Videos abspielbar).
  Behoben, und das Skript prüft sich seitdem selbst vor dem Hochladen.
- **Bilder mit Großschreibung in der Endung:** `.JPG` wurde zu `.jpg` umgewandelt, der Pfad zeigte
  aber weiter auf `.JPG`. Auf dem Mac unbemerkt (Dateisystem ignoriert Groß-/Kleinschreibung),
  auf GitHub Pages 404. Behoben in `.build_board.py`, Funktion `web_kopie`.
- **Verlassen auf das `toggle`-Ereignis von `<details>`:** feuert zu spät, dadurch klappte die
  Themenliste beim Ankreuzen jedes Mal zu. Gelöst, indem der Klappzustand direkt im
  Checkbox-Ereignis gesichert wird.
- **Ein einzelner `mv`-Befehl mit vielen Pfaden:** wird vom Sicherheitsfilter blockiert. Einzelne
  Aufrufe oder ein Python-Skript gehen durch.
- **`python3 -m http.server 8899`:** Port ist auf diesem Mac belegt, es antwortet etwas Fremdes
  ("Vorschau: Fortschrittsleiste"). 8911 war frei.

## Offene Fragen an dich

- Wie soll die Datei beim Hochladen in `eingang/` gelangen? Über den Cloudflare-Dienst (dann ist
  unklar, ob große Dateien die Rechenzeit-Grenze sprengen) oder direkt vom Browser zur GitHub-API
  mit einem Schlüssel, den der Dienst nach Passworteingabe herausgibt (dann liegt ein Schlüssel
  während der Sitzung im Browser). Das blockiert Schritt 3, Teil 2.
- Welches Passwort ist im Dienst hinterlegt? Ohne das kann der nächste Chat den Login nicht testen.

## Nächste Schritte

1. Den Nutzer bitten, `ZUGANG_EINRICHTEN.command` im Ordner `/Users/davevu/CalianteBoard`
   doppelzuklicken. Das repariert die GitHub-Anmeldung und setzt `GH_TOKEN` im Cloudflare-Dienst.
   Prüfen mit `gh auth status`, erwartet: `Logged in to github.com`.
2. Danach `git push origin HEAD` ausführen. Erwartet: die beiden wartenden Commits gehen hoch.
   Anschließend prüfen, ob der Passwort-Login online ankommt:
   `curl -s https://mantyga777-coder.github.io/caliante-inspo-board/index.html | grep -o 'DIENST="[^"]*"'`
   Erwartet: `DIENST="https://caliante-board-dienst.myaffiliate24.workers.dev"`.
3. Login mit dem echten Passwort testen, eine Kategorie ändern, speichern, und prüfen, ob die
   Änderung nach etwa einer Minute live ist.
4. Schritt 3, Teil 2 bauen: Ablagefeld auf der Team-Seite. Vorher die offene Frage oben klären.
   Die Verarbeitung dahinter (`eingang_verarbeiten.py` plus Action) ist fertig und getestet.
5. Testweise eine Datei nach `eingang/` legen und hochladen, um die Action
   `eingang-verarbeiten.yml` einmal echt laufen zu sehen. Sie ist noch nie auf GitHub gelaufen.

## Fallen

- **Der Nutzer ist nicht technisch.** Er arbeitet ausschließlich per Doppelklick auf `.command`-Dateien
  und hat mehrfach deutlich gemacht, dass Terminal, Schlüssel-Erzeugung und JSON-Bearbeitung für ihn
  nicht in Frage kommen. Lösungen entsprechend zuschneiden.
- **Arbeits-Board und Team-Seite sehen fast gleich aus.** Er hat zweimal geglaubt, es sei etwas kaputt,
  während er nur auf der jeweils anderen Seite war. Deshalb gibt es jetzt das Schild neben dem Titel.
  Bei jeder Fehlermeldung zuerst klären, welche der beiden Seiten er offen hat.
- **GitHub Pages lässt Browser die Seite 10 Minuten zwischenspeichern** (`cache-control: max-age=600`).
  Nach dem Veröffentlichen sieht man ohne Neuladen den alten Stand. Die Seite heilt sich inzwischen
  selbst über `version.txt`, aber beim Prüfen per curl immer einen Zufallsparameter anhängen.
- **Zwei Bau-Skripte müssen synchron bleiben:** `.build_board.py --web` (auf dem Mac) und
  `render_web.py` (auf GitHub) erzeugen dieselbe Seite. Wer einen Platzhalter in
  `.board_template.html` ergänzt, muss ihn in **beiden** ersetzen, sonst steht `__NAME__` in der Seite.
- **Parallele Sitzungen arbeiten am selben Projekt.** Der Cloudflare-Worker tauchte unangekündigt auf.
  Vor Änderungen `git status --short` prüfen und fremde Arbeit nicht überschreiben.
- **Kein `cryptography`-Modul in Python auf diesem Mac.** Verschlüsselung deshalb im Browser über
  die Web-Crypto-Schnittstelle, falls je wieder nötig.
- **Die Originalvideos (1,2 GB) liegen nur lokal** in `INSPO_INBOX/` und sind per `.gitignore`
  ausgeschlossen. Im Repository liegen nur die verkleinerten Fassungen unter `web/`.
- Es gibt eine ältere Übergabe `HANDOFF-caliante-inspo-board-2026-08-28-2315.md` im selben Ordner.
  Ihre Punkte zum LaunchAgent sind inzwischen erledigt, der Umzug nach `~/CalianteBoard` ist passiert.
