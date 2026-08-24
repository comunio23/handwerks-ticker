# -*- coding: utf-8 -*-
"""
Auswertung fuer Gremien und Argumentation - laeuft NICHT in der Web-App.

Beantwortet die Frage, um die es urspruenglich ging: Welche Themen fuehrt das
Handwerk wirklich, und welche laufen nur im Nebensatz mit?

Drei Spalten je Thema:
  genannt     - Meldungen, in denen das Thema ueberhaupt vorkommt
  mit Substanz- Meldungen, in denen es mindestens dreimal vorkommt
  Hauptthema  - Meldungen, deren Thema es laut Redaktion IST

Je weiter diese Zahlen auseinanderliegen, desto mehr wird ein Thema
mitgefuehrt, statt es zu fuehren.

Aufruf:
    python analyse-themen.py
"""
import json
import os
import re
import sys
import io

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

JAHR = "2026"
SCHWELLE = 3

# Stichworte je Thema. Die Themennamen sind DIESELBEN wie in
# daten/redaktion-2026.json - sonst zaehlt die Spalte "Hauptthema" ins Leere.
STICHWORTE = {
    "Entbürokratisierung":     ["bürokratie", "berichtspflicht", "genehmigungsverfahren"],
    "Steuern & Abgaben":       ["steuer", "handwerkerbonus", "abgabe"],
    "Auflagen & Vorschriften": ["auflage", "vorschrift", "parkausweis", "nachweispflicht"],
    "Personal & Fachkräfte":   ["fachkräfte", "fachkraft", "personal", "beschäftigte"],
    "Ausbildung & Nachwuchs":  ["ausbildung", "auszubildend", "azubi", "lehrstelle"],
    "Energie & Sprit":         ["energie", "kraftstoff", "diesel", "sprit", "strompreis"],
    "Aufträge & Vergabe":      ["vergabe", "öffentliche aufträge", "preisgleitklausel"],
    "Betrieb & Nachfolge":     ["nachfolge", "generationswechsel", "existenzgründ"],
    "Wirtschaftslage":         ["geschäftslage", "konjunktur", "auftragslage"],
    "Politik & Regierung":     ["landesregierung", "koalition", "ministerpräsident"],
}


def artikel_id(url):
    m = re.search(r"-\d+,\d+,(\d+)\.html", url)
    return m.group(1) if m else None


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    meldungen = json.load(open("daten/meldungen-%s.json" % JAHR, encoding="utf-8"))
    redaktion = json.load(open("daten/redaktion-%s.json" % JAHR,
                               encoding="utf-8"))["eintraege"]

    texte = {artikel_id(m["url"]): (m["volltext"] + " " + m["titel"]).lower()
             for m in meldungen}
    daten = {artikel_id(m["url"]): m for m in meldungen}

    # Gegenprobe: Steht jeder Themenname auch wirklich in der Redaktionsdatei?
    vergeben = set()
    for r in redaktion.values():
        vergeben.add(r["thema"])
        if r.get("thema2"):
            vergeben.add(r["thema2"])
    unbekannt = [t for t in STICHWORTE if t not in vergeben]
    if unbekannt:
        print("ACHTUNG - diese Themen gibt es in der Redaktionsdatei nicht:")
        for t in unbekannt:
            print("   ", t)
        print("   Die Spalte 'Hauptthema' waere fuer sie immer 0 und damit irrefuehrend.")
        print()

    zeilen = []
    for thema, worte in STICHWORTE.items():
        genannt = substanz = 0
        haupt = []
        for kennung, text in texte.items():
            treffer = sum(text.count(w) for w in worte)
            if treffer:
                genannt += 1
            if treffer >= SCHWELLE:
                substanz += 1
            r = redaktion.get(kennung)
            if r and (r["thema"] == thema or r.get("thema2") == thema):
                haupt.append(kennung)
        politisch = sum(1 for k in haupt if redaktion[k]["art"] == "politik")
        zeilen.append((thema, genannt, substanz, len(haupt), politisch, haupt))

    zeilen.sort(key=lambda z: -z[1])

    print("Themen im Jahrgang %s - %d Meldungen ausgewertet" % (JAHR, len(meldungen)))
    print("=" * 76)
    print("%-26s %8s %12s %11s %11s" %
          ("Thema", "genannt", "mit Substanz", "Hauptthema", "davon polit."))
    print("-" * 76)
    for thema, genannt, substanz, haupt, politisch, _ in zeilen:
        print("%-26s %8d %12d %11d %11d" % (thema, genannt, substanz, haupt, politisch))

    print()
    print("Auffaellig:")
    for thema, genannt, substanz, haupt, politisch, _ in zeilen:
        if genannt >= 8 and haupt == 0:
            print("  * %s: in %d Meldungen genannt, aber in keiner selbst zum Thema gemacht."
                  % (thema, genannt))
        elif genannt >= 8 and politisch == 0 and haupt:
            print("  * %s: %d eigene Meldungen, aber keine einzige politische Forderung."
                  % (thema, haupt))

    print()
    print("Absender der Meldungen:")
    absender = {}
    for k, r in redaktion.items():
        m = daten.get(k)
        if not m:
            continue
        kopf = m.get("kopfzeile", "")
        anfang = m["volltext"][:400]
        if kopf.lower().startswith("gemeinsame presse"):
            wer = "Gemeinsam mit Partnern"
        elif "Handwerkskammertag" in kopf or "Handwerkskammertag" in anfang:
            wer = "Handwerkskammertag Brandenburg"
        elif re.search(r"(Cottbus|Frankfurt \(Oder\))[/ ].*Potsdam|Potsdam/\s*Cottbus", anfang):
            wer = "Handwerkskammertag Brandenburg"
        else:
            wer = "Handwerkskammer Potsdam"
        absender.setdefault(wer, []).append(k)
    for wer, liste in sorted(absender.items(), key=lambda p: -len(p[1])):
        pol = sum(1 for k in liste if redaktion[k]["art"] == "politik")
        print("  %-32s %2d Meldungen, davon %d politisch" % (wer, len(liste), pol))


if __name__ == "__main__":
    main()
