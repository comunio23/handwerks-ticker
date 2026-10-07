# Handwerks-Ticker

Was das Handwerk gerade fordert – gebündelt aus fünf Quellen: den
Handwerkskammern **Potsdam**, **Frankfurt (Oder)** und **Cottbus**, dem
**Zentralverband des Deutschen Handwerks** und den **Junioren des Handwerks e.V.**
Damit ist Brandenburg vollständig abgedeckt.

**Live:** https://handwerks-ticker.netlify.app

---

## Der Abgleich

Eine Datei startet alles:

```
woechentlich-abgleichen.cmd
```

Doppelklicken genügt. Sie holt alle Quellen, baut den Ticker neu und
veröffentlicht ihn. Das dauert einige Minuten – der Abruf ist bewusst
langsam, damit die fremden Server nicht belastet werden.

### Automatisch jeden Mittwoch

Einmalig in der Eingabeaufforderung ausführen:

```
schtasks /create /tn "Handwerks-Ticker" /sc weekly /d MI /st 07:30 /tr "\"C:\Users\ZFG\Desktop\Themen-Standpunkte HWK\woechentlich-abgleichen.cmd\" still"
```

Täglich statt wöchentlich: `/sc daily /st 07:30` statt `/sc weekly /d MI /st 07:30`.

Wieder entfernen: `schtasks /delete /tn "Handwerks-Ticker" /f`
Nachsehen: `schtasks /query /tn "Handwerks-Ticker" /v /fo LIST`

Was bei jedem Lauf passierte, steht in `daten/abgleich-protokoll.txt`.

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
| `daten/quellen.json` | welche Quellen eingesammelt werden |
| `daten/bekannt.json` | was schon bekannt war (für die „Neu"-Markierung) |

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
```

Der Netlify-Token kommt aus der Umgebungsvariablen `NETLIFY_AUTH_TOKEN` und
steht nirgends im Code.
