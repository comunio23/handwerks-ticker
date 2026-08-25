# -*- coding: utf-8 -*-
"""
Sammelt die bundesweiten Veroeffentlichungen des Zentralverbands des Deutschen
Handwerks (ZDH) ein.

Zwei Quellen:
  1. Pressemitteilungen  /presse/veroeffentlichungen/pressemitteilungen/...
  2. ZDH-Positionen      /themen-und-positionen/zdh-positionen/...

Die URLs kommen aus der sitemap.xml. Achtung: Das lastmod der Sitemap ist beim
ZDH unbrauchbar als Erscheinungsdatum - sehr viele Seiten tragen denselben Tag
(Umzug des Systems). Das echte Datum steht auf der Seite selbst in der ersten
Zeile im Format TT.MM.JJJJ und wird von dort gelesen.

Hoeflicher Abruf: eigener User-Agent, eine Sekunde Pause nach jedem echten
Abruf, lokaler Cache unter daten/cache-zdh/. Die robots.txt des ZDH sperrt nur
/typo3/ und /suchergebnisse/ - beide werden nicht angefasst.

Aufruf:
    python scrape-zdh.py            (nur das laufende Jahr)
    python scrape-zdh.py 2025       (ein bestimmtes Jahr)
"""
import json
import re
import html
import sys
import time
import os
import datetime
import urllib.request

BASIS = "https://www.zdh.de"
UA = "Handwerks-Ticker/1.0 (Handwerksjunioren HWK Potsdam)"
CACHE = os.path.join("daten", "cache-zdh")

SITEMAP = BASIS + "/sitemap.xml"
DATUM_MUSTER = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
# Zeilen, die zum Seitengeruest gehoeren und nicht zum Text
GERUEST = re.compile(r"^(Schlagworte|Weitere Veröffentlichungen zum Thema|"
                     r"Bereichsleiter|Bereichsleiterin|Referent|Referentin|"
                     r"Pressesprecher|Generalsekretär|\+49 30|[\w.\-]+@zdh\.de)")


def hole(url, versuche=3):
    """Holt eine Seite. Bereits geholte Seiten kommen aus dem lokalen Cache."""
    os.makedirs(CACHE, exist_ok=True)
    schluessel = re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:] + ".html"
    pfad = os.path.join(CACHE, schluessel)
    if os.path.exists(pfad):
        return open(pfad, encoding="utf-8").read()
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                seite = r.read().decode("utf-8", errors="replace")
            open(pfad, "w", encoding="utf-8").write(seite)
            time.sleep(1)
            return seite
        except Exception as e:
            if i == versuche - 1:
                print("  FEHLER bei", url, "->", e, file=sys.stderr)
                return None
            time.sleep(2)


def nur_zeilen(seite):
    """Seiteninhalt als Liste lesbarer Zeilen."""
    m = re.search(r"<main.*?</main>", seite, re.S)
    body = m.group(0) if m else seite
    body = re.sub(r"(?is)<(script|style|nav|figure|form)\b.*?</\1>", " ", body)
    body = re.sub(r"(?is)<br\s*/?>", "\n", body)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", "\n", body))
    return [z.strip() for z in text.split("\n") if z.strip()]


def ist_inhaltsseite(url):
    """Uebersichtsseiten aussortieren. '/presse/veroeffentlichungen/
    pressemitteilungen/' ist eine Liste, erst der Pfad DAHINTER ist eine
    Meldung. Dasselbe gilt fuer die Positionen."""
    teile = [t for t in url.replace(BASIS, "").split("/") if t]
    if "/presse/veroeffentlichungen/pressemitteilungen/" in url:
        return len(teile) >= 4
    if "/zdh-positionen/" in url:
        return len(teile) >= 4
    return False


def urls_aus_sitemap():
    """Pressemitteilungs- und Positions-URLs samt lastmod aus der Sitemap."""
    index = hole(SITEMAP)
    if not index:
        sys.exit("Sitemap des ZDH nicht erreichbar.")
    unter = [u.replace("&amp;", "&")
             for u in re.findall(r"<loc>([^<]+\.xml[^<]*)</loc>", index)]
    if not unter:
        unter = [SITEMAP]

    gefunden = {}
    for u in unter:
        s = hole(u)
        if not s:
            continue
        for loc, lastmod in re.findall(
                r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", s):
            loc = loc.strip()
            if loc.endswith(".xml") or "sitemap=" in loc:
                continue
            if ist_inhaltsseite(loc):
                gefunden[loc] = lastmod.strip()[:10]
    return gefunden


def seite_lesen(url, lastmod=None):
    """Datum, Titel, Bereiche, Text und Schlagworte einer ZDH-Seite."""
    seite = hole(url)
    if not seite:
        return None
    zeilen = nur_zeilen(seite)
    if not zeilen:
        return None

    ist_position = "/zdh-positionen/" in url

    datum = None
    titel = ""
    start = 0
    for i, z in enumerate(zeilen[:4]):
        m = DATUM_MUSTER.match(z)
        if m:
            datum = "%s-%s-%s" % (m.group(3), m.group(2), m.group(1))
            titel = zeilen[i + 1] if i + 1 < len(zeilen) else ""
            start = i + 2
            break
    datum_quelle = "seite"
    if datum is None:
        # Positionspapiere tragen kein Datum auf der Seite. Ersatzweise das
        # lastmod der Sitemap - das ist ein Stand, kein Erscheinungsdatum,
        # und wird deshalb ausdruecklich als ungenau gekennzeichnet.
        titel = zeilen[0]
        start = 1
        datum = lastmod
        datum_quelle = "sitemap"

    # Schlagworte und Bereiche einsammeln, Geruestzeilen aus dem Text nehmen
    schlagworte = []
    if "Schlagworte" in zeilen:
        i = zeilen.index("Schlagworte")
        for z in zeilen[i + 1:i + 9]:
            if z.startswith("Weitere Ver"):
                break
            if len(z) < 40:
                schlagworte.append(z)

    ende = len(zeilen)
    for i in range(start, len(zeilen)):
        if zeilen[i].startswith(("Schlagworte", "Weitere Veröffentlichungen")):
            ende = i
            break

    text = [z for z in zeilen[start:ende]
            if not GERUEST.match(z) and len(z) > 25]

    return {
        "url": url,
        "datum": datum,
        "datum_quelle": datum_quelle,
        "titel": titel,
        "art_quelle": "position" if ist_position else "pressemitteilung",
        "schlagworte": schlagworte,
        "volltext": "\n".join(text).strip(),
        "quelle": "Zentralverband des Deutschen Handwerks",
        "ebene": "Bund",
    }


if __name__ == "__main__":
    hier = os.path.dirname(os.path.abspath(__file__))
    os.chdir(hier)

    jahr = sys.argv[1] if len(sys.argv) > 1 else str(datetime.date.today().year)
    print("ZDH-Abruf, Jahrgang", jahr)

    urls = urls_aus_sitemap()
    print("Inhaltsseiten in der Sitemap:", len(urls))

    ergebnis = []
    ohne_datum = 0
    for i, (u, lastmod) in enumerate(sorted(urls.items()), 1):
        eintrag = seite_lesen(u, lastmod)
        if not eintrag or not eintrag["titel"]:
            continue
        if eintrag["datum"] is None:
            ohne_datum += 1
        elif not eintrag["datum"].startswith(jahr):
            continue
        if len(eintrag["volltext"]) < 200:
            continue
        ergebnis.append(eintrag)
        if i % 25 == 0:
            print("  ... %d von %d geprueft" % (i, len(urls)))

    ergebnis.sort(key=lambda x: (x["datum"] or "0000"), reverse=True)
    ziel = os.path.join("daten", "zdh-%s.json" % jahr)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=2)

    presse = sum(1 for x in ergebnis if x["art_quelle"] == "pressemitteilung")
    ungenau = sum(1 for x in ergebnis if x["datum_quelle"] == "sitemap")
    print()
    print("Uebernommen:", len(ergebnis),
          "(%d Pressemitteilungen, %d Positionen; davon %d mit ungenauem Datum)"
          % (presse, len(ergebnis) - presse, ungenau))
    print("Geschrieben:", ziel)
