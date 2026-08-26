# Handwerks-Ticker

Was das Handwerk gerade fordert – gebündelt aus den Veröffentlichungen der
Handwerkskammer Potsdam, des Handwerkskammertages Brandenburg und des
Zentralverbands des Deutschen Handwerks.

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
| `daten/redaktion-2026.json` | Schlagzeile, Dreizeiler, Thema je Kammer-Meldung |
| `daten/redaktion-zdh-2026.json` | Dreizeiler und Thema je ZDH-Meldung |
| `daten/forderungen.json` | die drei Top-Forderungen samt Belegen |
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
