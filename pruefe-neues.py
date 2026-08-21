# -*- coding: utf-8 -*-
"""
Taeglicher Abgleich: Gibt es neue Pressemitteilungen?

  1. Uebersichtsseite frisch holen (der Cache wird dafuer uebergangen)
  2. nur die NEUEN Artikelseiten nachladen - alte kommen aus dem Cache
  3. daten/meldungen-<jahr>.json neu schreiben
  4. ticker-prototyp.html neu bauen; neue Meldungen stehen dort oben

Aufruf:
    python pruefe-neues.py

Fuer den taeglichen Lauf gibt es taeglich-pruefen.cmd - siehe dort.
Rueckgabewert: 0 = nichts Neues, 1 = es gibt neue Meldungen, 2 = Fehler.
"""
import json
import os
import re
import sys
import datetime
import subprocess

import importlib.util

HIER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HIER)

spec = importlib.util.spec_from_file_location("scraper", "scrape-pressemitteilungen.py")
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)

JAHR = str(datetime.date.today().year)
UEBERSICHT_STANDARD = (scraper.BASIS +
                       "/artikel/pressemitteilungen-2026-9,735,6713.html")


def uebersicht_url():
    """Die Uebersichtsseite traegt die Jahreszahl im Namen. Zum Jahreswechsel
    aendert sie sich - deshalb wird sie in der Navigation gesucht, statt sie
    fest zu verdrahten."""
    start = scraper.hole(scraper.BASIS + "/")
    if start:
        treffer = re.findall(r'href="(/artikel/pressemitteilungen-(\d{4})-[^"]+)"', start)
        if treffer:
            neuste = max(treffer, key=lambda t: t[1])
            return scraper.BASIS + neuste[0]
    return UEBERSICHT_STANDARD


def main():
    datei = "daten/meldungen-%s.json" % JAHR
    vorher = set()
    if os.path.exists(datei):
        vorher = {scraper.artikel_id(m["url"])
                  for m in json.load(open(datei, encoding="utf-8"))}

    # Startseite, Uebersicht und Sitemap muessen frisch sein, sonst faellt nie
    # etwas Neues auf. Die einzelnen Artikelseiten bleiben im Cache - die
    # aendern sich nach dem Erscheinen nicht mehr.
    if os.path.isdir(scraper.CACHE):
        for name in os.listdir(scraper.CACHE):
            if ("pressemitteilungen" in name or "sitemap" in name
                    or name == "https_www_hwk_potsdam_de_.html"):
                os.remove(os.path.join(scraper.CACHE, name))

    url = uebersicht_url()
    print("Abgleich am %s" % datetime.date.today().isoformat())
    print("Uebersicht:", url)

    liste = scraper.uebersicht_einsammeln(url)
    lastmod = scraper.sitemap_daten()

    ergebnis = []
    neue = []
    for e in liste:
        kennung = scraper.artikel_id(e["url"])
        if kennung not in vorher:
            neue.append(kennung)
        a = scraper.artikel_holen(e, lastmod)
        if a:
            ergebnis.append(a)

    for i, a in enumerate(ergebnis):
        if a["datum"]:
            continue
        nachbar = next((ergebnis[j]["datum"] for j in range(i - 1, -1, -1)
                        if ergebnis[j]["datum"]), None)
        if not nachbar:
            nachbar = next((ergebnis[j]["datum"] for j in range(i + 1, len(ergebnis))
                            if ergebnis[j]["datum"]), None)
        if nachbar:
            a["datum"], a["datum_quelle"] = nachbar, "eingeordnet"

    ergebnis.sort(key=lambda x: (x["datum"] or ""), reverse=True)
    json.dump(ergebnis, open(datei, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print("Meldungen gesamt:", len(ergebnis))

    if not neue:
        print("Nichts Neues.")
    else:
        print("NEU (%d):" % len(neue))
        for a in ergebnis:
            if scraper.artikel_id(a["url"]) in neue:
                print("   %s  %s" % (a["datum"], a["titel"][:70]))
        print()
        print("Diese Meldungen haben noch keinen Eintrag in")
        print("daten/redaktion-%s.json - sie erscheinen bis dahin mit dem" % JAHR)
        print("Originaltitel der Kammer und der Markierung 'Noch nicht eingeordnet'.")

    print()
    print("Ticker neu bauen ...")
    lauf = subprocess.run([sys.executable, "baue-ticker.py"])
    if lauf.returncode != 0:
        return 2
    return 1 if neue else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as fehler:      # damit der Zeitplan-Lauf nicht stumm scheitert
        print("FEHLER beim Abgleich:", fehler)
        sys.exit(2)
