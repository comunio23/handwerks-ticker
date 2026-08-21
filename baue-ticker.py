# -*- coding: utf-8 -*-
"""
Baut aus den eingesammelten Meldungen und der redaktionellen Ebene die
fertige Einzeldatei ticker-prototyp.html.

  daten/meldungen-2026.json   <- vom Scraper, unveraendert aus der Quelle
  daten/redaktion-2026.json   <- Schlagzeile, Dreizeiler, Thema, Art (redaktionell)
  vorlage-ticker.html         <- Geruest mit Platzhalter
        =>  ticker-prototyp.html

Wichtig: Woertliche Zitate werden NICHT umformuliert. Sie werden aus dem
Volltext der Pressemitteilung exakt uebernommen - nur dann, wenn die
Redaktionsdatei "zitat_zeigen": true setzt und ein Zitat gefunden wird.
"""
import json
import re
import os
import sys
import datetime

JAHR = "2026"
MIN_ZITAT = 120     # kuerzere Anfuehrungen sind meist Projekt- oder Titelnamen
MAX_ZITAT = 2000    # Statements der Praesidenten sind oft ein ganzer Absatz
ANZEIGE_ZITAT = 320  # so lang darf das Zitat auf der Karte hoechstens werden

ZITAT_MUSTER = re.compile(r"[„“\"]([^“”\"]{%d,%d})[“”\"]" % (MIN_ZITAT, MAX_ZITAT))
SATZ_ENDE = re.compile(r"[.!?](?=\s|$)")


def artikel_id(url):
    m = re.search(r"-\d+,\d+,(\d+)\.html", url)
    return m.group(1) if m else None


def zitat_finden(volltext):
    """Erstes ausreichend langes woertliches Zitat, exakt wie in der Quelle.

    Lange Statements werden am Satzende gekuerzt - nie mitten im Satz und
    nie mit veraenderten Worten. Gekuerzt wird nur hinten, der Anfang bleibt
    immer der Anfang des Zitats."""
    m = ZITAT_MUSTER.search(volltext)
    if not m:
        return None
    zitat = " ".join(m.group(1).split())
    if len(zitat) <= ANZEIGE_ZITAT:
        return zitat

    # letztes Satzende, das noch in die Anzeige passt
    enden = [t.end() for t in SATZ_ENDE.finditer(zitat) if t.end() <= ANZEIGE_ZITAT]
    if enden:
        return zitat[:enden[-1]]
    # ein einziger sehr langer Satz: lieber den ganzen ersten Satz zeigen
    erstes = SATZ_ENDE.search(zitat)
    return zitat[:erstes.end()] if erstes else zitat[:ANZEIGE_ZITAT]


def main():
    hier = os.path.dirname(os.path.abspath(__file__))
    os.chdir(hier)

    meldungen = json.load(open("daten/meldungen-%s.json" % JAHR, encoding="utf-8"))
    redaktion_datei = json.load(open("daten/redaktion-%s.json" % JAHR, encoding="utf-8"))
    redaktion = redaktion_datei["eintraege"]

    fertig = []
    ohne_redaktion = []
    zitate = 0

    for m in meldungen:
        kennung = artikel_id(m["url"])
        r = redaktion.get(kennung)
        if not r:
            ohne_redaktion.append((kennung, m["titel"][:60]))
            continue

        zitat = None
        if r.get("zitat_zeigen"):
            zitat = zitat_finden(m["volltext"])
            if zitat:
                zitate += 1
            else:
                print("  Hinweis: kein Zitat gefunden fuer %s (%s)"
                      % (kennung, m["titel"][:45]))

        fertig.append({
            "id": kennung,
            "datum": m["datum"],
            "datum_ungenau": m["datum_quelle"] == "eingeordnet",
            "nummer": m["nummer"],
            "titel": m["titel"],
            "url": m["url"],
            "art": r["art"],
            "thema": r["thema"],
            "schlagzeile": r["schlagzeile"],
            "dreizeiler": r["dreizeiler"],
            "zitat": zitat,
        })

    if ohne_redaktion:
        print("ABBRUCH - diese Meldungen haben keinen Redaktionseintrag:")
        for k, t in ohne_redaktion:
            print("   ", k, t)
        sys.exit(1)

    # Themen in der Reihenfolge ihrer Haeufigkeit, damit die Auswahl nuetzlich sortiert ist
    haeufigkeit = {}
    for x in fertig:
        haeufigkeit[x["thema"]] = haeufigkeit.get(x["thema"], 0) + 1
    themen = sorted(haeufigkeit, key=lambda t: (-haeufigkeit[t], t))

    daten = {
        "jahr": JAHR,
        "stand": redaktion_datei.get("stand", datetime.date.today().isoformat()),
        "themen": themen,
        "meldungen": fertig,
    }

    vorlage = open("vorlage-ticker.html", encoding="utf-8").read()
    platzhalter = re.search(r"/\*__DATEN__\*/.*?/\*__DATEN_ENDE__\*/", vorlage, re.S)
    if not platzhalter:
        sys.exit("Platzhalter in vorlage-ticker.html nicht gefunden.")

    # </script> im JSON wuerde den Script-Block vorzeitig beenden
    roh = json.dumps(daten, ensure_ascii=False, indent=1).replace("</", "<\\/")
    seite = vorlage.replace(platzhalter.group(0),
                            "/*__DATEN__*/" + roh + "/*__DATEN_ENDE__*/")

    with open("ticker-prototyp.html", "w", encoding="utf-8") as f:
        f.write(seite)

    print("Meldungen:", len(fertig))
    print("Zitate uebernommen:", zitate)
    print("Themen:", ", ".join("%s (%d)" % (t, haeufigkeit[t]) for t in themen))
    print("Geschrieben: ticker-prototyp.html (%.0f kB)" % (len(seite) / 1024))


if __name__ == "__main__":
    main()
