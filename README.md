# Handwerks-Ticker

Was das Handwerk gerade fordert – gebündelt aus fünf Quellen: den
Handwerkskammern **Potsdam**, **Frankfurt (Oder)** und **Cottbus**, dem
**Zentralverband des Deutschen Handwerks** und den **Junioren des Handwerks e.V.**
Damit ist Brandenburg vollständig abgedeckt.

Dazu kommt eine sechste Quelle, die **nicht** zum Handwerk gehört: das
**Ministerium für Wirtschaft, Energie, Klimaschutz und Europa**. Es ist der
Adressat vieler Forderungen – wer wissen will, ob eine Forderung beantwortet
wurde, muss auch die Gegenseite hören. Jede Meldung trägt deshalb ein Feld
`seite` („Handwerk" oder „Landesregierung"); Meldungen des Ministeriums
erscheinen mit einem dunklen Schild **Landesregierung** und auf leicht
abgesetzter Fläche, damit sie keine Sekunde lang wie eine Forderung des
Handwerks aussehen.

**Live:** https://handwerks-ticker.netlify.app

---

## Der Abgleich

Eine Datei startet alles:

```
abgleich-automatisch.cmd
```

Doppelklicken genügt. Sie holt alle Quellen, baut den Ticker neu und
veröffentlicht ihn. Das dauert einige Minuten – der Abruf ist bewusst
langsam, damit die fremden Server nicht belastet werden.

### Automatisch mittwochs und freitags

Einmalig ausführen – danach läuft es von selbst:

```
powershell -ExecutionPolicy Bypass -File automatik-einschalten.ps1
```

**Warum diese beiden Tage?** Gemessen am Jahrgang 2026 (412 Meldungen)
erscheint dienstags mit Abstand am meisten (136), am Wochenende fast nichts.
Mit Mittwoch **und** Freitag liegt eine Meldung im Schnitt **2,0 Tage**
unbemerkt herum, mit einem einzigen Tag 3,7 Tage.

| Takt | mittlere Liegezeit |
|---|---|
| nur mittwochs | 3,7 Tage |
| nur freitags | 3,3 Tage |
| **mittwochs + freitags** | **2,0 Tage** |
| täglich | 1,0 Tage |

War der Rechner um 7:30 aus, holt Windows den Lauf beim nächsten Start nach.
Bei Netzproblemen gibt es drei Versuche im Stundenabstand.

Wieder abschalten: `powershell -ExecutionPolicy Bypass -File automatik-einschalten.ps1 -Aus`
Nachsehen: `Get-ScheduledTaskInfo -TaskName "Handwerks-Ticker"`

Wird der Takt geändert, muss auch `daten/quellen.json` geändert werden –
die Seite nennt den Takt, der dort steht.

Was bei jedem Lauf passierte, steht in `daten/abgleich-protokoll.txt`.

### Fällt die Automatik aus, sagt es die Seite

Ein Zeitplan fällt still aus. Deshalb rechnet der Ticker beim Öffnen selbst
nach: Liegt der letzte Abgleich mehr als **acht Tage** zurück, erscheint oben
ein oranger Hinweis. Acht Tage, weil der größte normale Abstand (Freitag bis
Mittwoch) fünf Tage beträgt – ein einzelner verpasster Lauf soll keinen
Fehlalarm auslösen.

Dafür gibt es zwei getrennte Daten, die lange eines waren:

| Feld | Bedeutung |
|---|---|
| `letzter_abgleich` | wann die Quellen zuletzt **wirklich abgefragt** wurden (aus `daten/abgleich-stand.json`, geschrieben von `abgleich.py`) |
| `letztes_neues` | wann zuletzt **etwas Neues** dabei war |

Vorher wurde beides aus dem jüngsten Fund abgeleitet – ein Abgleich, bei dem
nichts Neues dabei war, sah damit aus wie gar kein Abgleich.

---

## Als App auf dem Handy

Die Live-Seite lässt sich auf dem Handy wie eine App installieren
(Progressive Web App) – mit eigenem Symbol auf dem Startbildschirm, ohne
Adressleiste und **ohne App Store**.

- **Android/Chrome:** Beim ersten Besuch erscheint oben die Frage „Diesen
  Ticker als App installieren?" – antippen, fertig. Wer sie wegtippt, findet
  den Weg weiter im Chrome-Menü unter *App installieren*.
- **iPhone:** Safari kennt diesen Knopf nicht. Dort steht stattdessen der
  Hinweis: *Teilen* → *Zum Home-Bildschirm*.

**Sie funktioniert auch ohne Netz.** Der Service Worker (`web/sw.js`) fragt
immer zuerst das Netz und legt die Antwort beiseite; nur wenn keine
Verbindung da ist, zeigt er die zuletzt gespeicherte Fassung. Umgekehrt wäre
die Seite schneller, würde aber alte Meldungen zeigen – bei einem Ticker der
schlechtere Tausch.

Ausgeliefert wird dafür nicht mehr nur eine Datei:

| lokal | live unter |
|---|---|
| `ticker-prototyp.html` | `/index.html` |
| `web/manifest.json` | `/manifest.json` |
| `web/sw.js` | `/sw.js` |
| `web/icons/*.png` | `/icons/*.png` |

Vor dem Veröffentlichen genau das ansehen, was hochgeht:

```
python deploy-netlify.py --vorschau
python -m http.server 8766 --directory vorschau
```

Die **heruntergeladene Einzeldatei** bleibt davon unberührt: Sie enthält alle
Meldungen und funktioniert vollständig, nur Installation und Symbol fehlen
(ein Service Worker braucht http(s), aus `file://` gibt es ihn nicht).

---

## Quellen festlegen

Welche Bereiche eingesammelt werden, steht in **`daten/quellen.json`**.
Dort lässt sich ein Bereich mit `"aktiv": false` abschalten oder ein neuer
hinzufügen – ohne den Code anzufassen.

Derzeit aktiv beim ZDH:

| Bereich | im Ticker |
|---|---|
| Pressemitteilungen | ja |
| Interviews & Statements | ja |
| Reden & Namensbeiträge | ja |
| ZDH-Positionen | **nein** – siehe unten |
| Personalia | abgeschaltet (politisch ohne Gewicht) |

### Handwerkskammer Frankfurt (Oder)

Läuft auf WordPress mit offener Schnittstelle – Datum, Titel, Anrisstext,
Volltext und Kategorien kommen als JSON, es wird nichts aus HTML geraten.
Welche Kategorien eingesammelt werden, steht in `daten/quellen.json`:

| Kategorie | im Ticker |
|---|---|
| Medieninformationen | ja (die Pressemeldungen der Kammer selbst) |
| Handwerksjunioren | ja |
| Presse | **nein** – Obermenge mit Lehrberufeschauen und Fotogalerien |
| Recht, Fotogalerien, Sonderumfragen | nein |

### Handwerkskammer Cottbus

Gleiches Redaktionssystem wie Potsdam, aber **monatsweise** geordnet:
Archiv → Monatsseite → Meldung.

**Achtung, hier liegt eine Falle:** Die `sitemap.xml` der Kammer endet im
Dezember 2024. Wer ihr vertraut, hält die Quelle für seit zwei Jahren tot –
die Seite selbst ist aktuell. Der Abruf geht deshalb über die Archivseite.

Die Meldungen tragen **kein Datum im Text**. Es kommt aus dem Feld
`datePublished`, dessen sichtbare Beschriftung „Seite aktualisiert am …"
lautet. Bei 13 von 58 Meldungen widerspricht dieses Datum dem Monat, unter
dem die Kammer die Meldung führt – dann war es eine spätere Bearbeitung.
Diese Meldungen erscheinen mit „um den …" und nennen beim Antippen den Grund.
Ein Ersatzdatum wird **nicht** erfunden.

### Junioren des Handwerks (Bundesverband)

| Bereich | im Ticker |
|---|---|
| PRESSE (Abschnitt der Startseite) | ja |
| TERMINE (Abschnitt der Startseite) | ja, aber nur **künftige** |

Diese Quelle ist ein Sonderfall: handwerksjunioren.de hat **keinen
Nachrichtenstrom**. Alle Inhalte stehen auf der Startseite, es gibt keine
eigene Adresse je Meldung. Die Kennung bildet der Abruf deshalb aus Datum und
Titel; verlinkt wird der Seitenanker. Vergangene Termine bleiben weg, weil zu
fast jedem im Abschnitt PRESSE schon ein Bericht steht – umstellbar über
`"nur_kuenftige": false` in `daten/quellen.json`.

Die beiden **Maßnahmenpapiere** (Mutterschutz, Lohnzusatzkosten) stehen dort
nur als Bild. Ihr Text ist nicht maschinell lesbar; Kurzfassung und Zitat
wurden von den Bildseiten abgelesen und stehen mit Herkunftsvermerk in
`daten/redaktion-handwerksjunioren-2026.json`.

**Warum die Positionspapiere nicht in der Zeitleiste stehen:** Sie tragen kein
Erscheinungsdatum auf der Seite, und die Sitemap liefert bei 63 von 64 den Tag
der Systemumstellung. Sie als „vom 7. Juli" anzuzeigen wäre eine erfundene
Tatsache. Als Beleg für eine Forderung bleiben sie nutzbar – dort zählt der
Inhalt, nicht das Datum.

### Wirtschaftsministerium Brandenburg – die Gegenseite

```
python scrape-mweke.py
```

Das Ministerium ist **keine Handwerksquelle**, sondern der Adressat. Seine
Meldungen tragen `seite: "Landesregierung"`, erscheinen mit dem dunklen Schild
**Landesregierung** und sind über den Knopf *Ministerium* einzeln zu holen.

Drei Eigenheiten der Seite:

1. **Die Domain wechselt** je nach Zuschnitt des Hauses (mwae → mwaek →
   mweke), alle zeigen auf dieselbe Installation. Jeder Verweis wird auf die
   in `quellen.json` hinterlegte Basis umgeschrieben – sonst stünde dieselbe
   Meldung unter zwei Adressen in den Daten.
2. **Die Presseliste zeigt immer nur 15 Meldungen** und kennt kein Blättern.
   Dafür gibt es Rubriken, die je 15 eigene Meldungen führen; bei schmalen
   Rubriken reicht das Jahre zurück. Gesammelt wird deshalb über die Rubriken.
   Aktiv sind *Handel und Handwerk*, *Ausbildung, Arbeit*, *Energie*,
   *Förderpolitik*, *Gründungsförderung*, *Schule und Wirtschaft* – und die
   Gesamtliste, damit nichts Aktuelles durchrutscht, nur weil es in keiner
   dieser Rubriken steht. Sie bringt ein paar Meldungen ohne Handwerksbezug
   mit; die sammeln sich zugeklappt unter *Aus der Landesregierung*.
3. **Das Datum steht zweimal da** – in der Liste und in der Meldung selbst
   („Potsdam, 1. Oktober 2026"). Beide werden verglichen; weichen sie ab,
   wird die Meldung als `datum_ungenau` gekennzeichnet, statt sie
   stillschweigend einem Tag zuzuordnen.

Eine `robots.txt` gibt es nicht (HTTP 404), es ist also nichts gesperrt. Der
Abruf bleibt trotzdem höflich: eigener User-Agent, eine Sekunde Pause,
lokaler Cache.

---

## Was wo steht

| Datei | Inhalt |
|---|---|
| `daten/meldungen-2026.json` | Kammer-Meldungen, unverändert aus der Quelle |
| `daten/zdh-2026.json` | ZDH-Veröffentlichungen, unverändert aus der Quelle |
| `daten/hwk-ff-2026.json` | Meldungen aus Frankfurt (Oder), unverändert |
| `daten/hwk-cottbus-2026.json` | Meldungen aus Cottbus, unverändert |
| `daten/handwerksjunioren-2026.json` | Junioren-Meldungen, unverändert aus der Quelle |
| `daten/redaktion-2026.json` | Schlagzeile, Dreizeiler, Thema je Kammer-Meldung |
| `daten/redaktion-zdh-2026.json` | Dreizeiler und Thema je ZDH-Meldung |
| `daten/redaktion-handwerksjunioren-2026.json` | Einordnung je Junioren-Meldung |
| `daten/forderungen.json` | die Top-Forderungen samt Belegen (Zahl frei) |
| `daten/mweke-2026.json` | Meldungen des Wirtschaftsministeriums, unverändert |
| `daten/redaktion-hwk-ff-2026.json` | Einordnung und Kurzfassungen Frankfurt (Oder) |
| `daten/redaktion-hwk-cottbus-2026.json` | Einordnung und Kurzfassungen Cottbus |
| `daten/quellen.json` | welche Quellen eingesammelt werden |
| `daten/bekannt.json` | was schon bekannt war (für die „Neu"-Markierung) |
| `daten/abgleich-stand.json` | wann zuletzt wirklich abgeglichen wurde |
| `web/manifest.json`, `web/sw.js`, `web/icons/` | was die Seite zur App macht |

---

## Die redaktionelle Ebene

Zu jeder Quelle gehört eine Redaktionsdatei, die einordnet, was die Quelle
selbst nicht sagt: `art` (politik / bericht / zahlen / ehrung / termin),
`thema`, optional `thema2`, eine eigene `schlagzeile` und ein `dreizeiler`.

| Eintrag | Wirkung |
|---|---|
| nur `art` und `thema` | ordnet ein; es bleibt beim **Anrisstext der Quelle**, sichtbar gekennzeichnet |
| zusätzlich `dreizeiler` | eigene Kurzfassung statt des Anrisstextes |
| zusätzlich `schlagzeile` | eigene Überschrift – nur wo der Originaltitel die Aussage nicht trägt |
| zusätzlich `zitat` | wörtliches Zitat als Blockzitat auf der Karte |

**`art: "politik"` vergibt nur ein Mensch.** Die automatische Erkennung
(`gattung_raten`) kennt Ehrung, Termin und Zahlen – „politisch" ist eine
redaktionelle Entscheidung und wird nie geraten.

**Jedes `zitat` wird geprüft.** Steht es nicht wörtlich im Volltext der
Quelle, **bricht der Bau ab**. Einzige Ausnahme: Liefert die Quelle gar
keinen Text, weil sie nur als Bild vorliegt (die Maßnahmenpapiere der
Junioren), muss der Eintrag in `quelle_text` festhalten, woher das Zitat
stammt. Die Pflicht zum Beleg bleibt, nur ihre Form ändert sich.

---

## Zwei Regeln, die nicht verhandelbar sind

**1. Nichts wird erfunden.** Jede Zahl und jedes Zitat muss wörtlich in der
Quelle stehen. Bei den Top-Forderungen ist das technisch erzwungen: Fehlt der
hinterlegte Beleg im Originaltext, **bricht der Bau ab** – ein Fehler
verhindert die Veröffentlichung, statt still durchzurutschen.

**2. Neue Meldungen fallen nicht unter den Tisch.** Wer noch keinen
Redaktionseintrag hat, erscheint trotzdem sofort: mit dem **Originaltitel der
Quelle** und deren **eigenem Anrisstext**, gekennzeichnet als solcher. So ist
der Ticker nach jedem Abgleich vollständig, ohne dass jemand etwas
dazuschreiben muss.

---

## Einzelne Schritte

```
python abgleich.py                 alle Quellen holen und bauen
python abgleich.py --hochladen     zusätzlich veröffentlichen
python baue-ticker.py              nur neu bauen
python deploy-netlify.py           nur veröffentlichen
python analyse-themen.py           Auswertung für Gremien
python deploy-netlify.py --vorschau   alles in den Ordner vorschau/, kein Upload
```

Der Netlify-Token kommt aus der Umgebungsvariablen `NETLIFY_AUTH_TOKEN` und
steht nirgends im Code.
