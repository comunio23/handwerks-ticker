# -*- coding: utf-8 -*-
"""
Sammelt die Pressemitteilungen der Handwerkskammer Cottbus ein.

Die Kammer nutzt dasselbe Redaktionssystem wie Potsdam (Adressmuster
-7,0,ID.html gegen -9,735,ID.html), ordnet ihre Meldungen aber MONATSWEISE:

    Archiv Pressemitteilungen
      -> Pressemitteilungen September 2026
           -> die einzelnen Meldungen

ACHTUNG, hier liegt die Falle: Die sitemap.xml der Kammer endet im Dezember
2024. Wer ihr vertraut, haelt die Quelle fuer seit zwei Jahren tot - die
Seite selbst ist aktuell. Deshalb laeuft der Abruf ueber die Archivseite der
Kammer, nicht ueber die Sitemap.

Zweite Besonderheit: Die Meldungen tragen kein Datum im Text. Das Datum kommt
aus dem Feld <time itemprop="datePublished"> der Seite. Dessen sichtbare
Beschriftung lautet "Seite aktualisiert am ..." - das System fuehrt es als
Veroeffentlichungsdatum, und an drei Stichproben lag es jeweils im richtigen
Monat. Wird eine Seite spaeter ueberarbeitet, kann das Datum wandern.

Hoeflicher Abruf: eigener User-Agent, eine Sekunde Pause, lokaler Cache.
Archiv- und Monatsseiten werden bei jedem Lauf frisch geholt (KMS [L-0248]),
die einzelnen Meldungen bleiben im Cache. Die robots.txt sperrt /downloads/,
/images/, /upload/ und weitere - /artikel/ ist frei.

Aufruf:
    python scrape-hwk-cottbus.py            (nur das laufende Jahr)
    python scrape-hwk-cottbus.py 2025       (ein bestimmtes Jahr)
"""
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.request

BASIS = "https://www.hwk-cottbus.de"
UA = "Handwerks-Ticker/1.0 (Handwerksjunioren HWK Potsdam)"
CACHE = os.path.join("daten", "cache-cottbus")

MONATE = {"januar": 1, "februar": 2, "maerz": 3, "märz": 3, "april": 4,
          "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
          "oktober": 10, "november": 11, "dezember": 12}

DATUM_MUSTER = re.compile(
    r'datePublished"[^>]*>[^<]*?(\d{1,2})\.\s*([A-Za-zÄÖÜäöü]+)\s+(\d{4})')
ARTIKEL_MUSTER = re.compile(r'href="(/artikel/[^"]*?-7,0,(\d+)\.html)"')

# Gattungszeile direkt unter dem Titel
GATTUNG = re.compile(r"^(Medieneinladung|Presseeinladung|Pressemitteilung|"
                     r"Pressemeldung|Presseinformation|Medieninformation)$", re.I)
FUSS = re.compile(r"^(Ansprechpartner|Pressesprecher|Downloads?$|Kontakt$|"
                  r"Weitere Informationen$|Tel\.|Telefon|E-Mail)", re.I)


def hole(url, frisch=False, versuche=3):
    """Holt eine Seite. Verzeichnisseiten immer frisch, Meldungen aus dem Cache."""
    os.makedirs(CACHE, exist_ok=True)
    schluessel = re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:] + ".html"
    pfad = os.path.join(CACHE, schluessel)
    if not frisch and os.path.exists(pfad):
        return open(pfad, encoding="utf-8").read()
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                seite = r.read().decode("utf-8", errors="replace")
            open(pfad, "w", encoding="utf-8").write(seite)
            time.sleep(1)
            return seite
        except Exception as e:
            if i == versuche - 1:
                print("  FEHLER bei", url, "->", e, file=sys.stderr)
                return None
            time.sleep(2)


def inhalt(seite):
    """Nur der Inhaltsbereich, ohne Kopf, Navigation und Fuss."""
    m = re.search(r'<div class="container content".*?(?=<footer|</body)', seite, re.S)
    return m.group(0) if m else seite


def zeilen_von(roh):
    t = re.sub(r"(?is)<(script|style|nav|figure|form)\b.*?</\1>", " ", roh)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", "\n", t))
    t = t.replace(" ", " ")
    return [re.sub(r"[ \t]+", " ", z).strip() for z in t.split("\n") if z.strip()]


def monatsseiten(jahr):
    """Die Monatsseiten des Jahrgangs - aus dem Archiv der Kammer, NICHT aus
    der Sitemap (die endet 2024)."""
    seite = hole(BASIS + "/artikel/archiv-pressemitteilungen-7,0,79.html", frisch=True)
    if not seite:
        sys.exit("Archivseite der Handwerkskammer Cottbus nicht erreichbar.")
    gefunden = {}
    muster = re.compile(
        r'href="(/artikel/pressemitteilungen-([a-zä]+)-(%s)-7,0,\d+\.html)"' % jahr,
        re.I)
    for pfad, monat, _ in muster.findall(seite):
        nummer = MONATE.get(monat.lower())
        if nummer:
            gefunden[nummer] = BASIS + pfad
    return [gefunden[n] for n in sorted(gefunden)]


def anrisse_von(monatsseite):
    """Je Meldung Dachzeile, Titel und Anrisstext - die Kammer liefert sie
    auf der Monatsseite mit, das spart Rateaufwand auf der Meldungsseite."""
    roh = inhalt(monatsseite)
    ergebnis = {}
    for block in re.findall(r'(?is)<div class="teaser-text">(.*?)</div>\s*</div>\s*'
                            r'<a class="teaser-link" href="([^"]+)"', roh):
        text, pfad = block
        m = re.search(r'(?is)<h2[^>]*>(?:<span[^>]*>(.*?)</span>)?(.*?)</h2>', text)
        if not m:
            continue
        dach = html.unescape(re.sub(r"<[^>]+>", "", m.group(1) or "")).strip()
        titel = html.unescape(re.sub(r"<[^>]+>", "", m.group(2) or "")).strip()
        a = re.search(r'(?is)<div class="small">(.*?)</div>', text)
        anriss = " ".join(zeilen_von(a.group(1))) if a else ""
        kennung = re.search(r"-7,0,(\d+)\.html", pfad)
        if kennung and titel:
            ergebnis[kennung.group(1)] = {
                "url": BASIS + pfad, "dachzeile": dach,
                "titel": titel, "anriss": anriss}
    return ergebnis


def monat_von(url):
    """Der Monat, unter dem die Kammer eine Monatsseite fuehrt."""
    m = re.search(r"pressemitteilungen-([a-zä]+)-\d{4}", url, re.I)
    return MONATE.get(m.group(1).lower()) if m else None


def meldung_lesen(eintrag):
    seite = hole(eintrag["url"])
    if not seite:
        return None

    m = DATUM_MUSTER.search(seite)
    if not m:
        return None
    nummer = MONATE.get(m.group(2).lower())
    if not nummer:
        return None
    try:
        datum = datetime.date(int(m.group(3)), nummer, int(m.group(1))).isoformat()
    except ValueError:
        return None

    zeilen = zeilen_von(inhalt(seite))
    ende = len(zeilen)
    for i, z in enumerate(zeilen):
        if FUSS.match(z):
            ende = i
            break
    # Dachzeile, Titel und Gattungszeile gehoeren nicht in den Fliesstext
    weg = {eintrag["dachzeile"], eintrag["titel"]}
    text = [z for z in zeilen[:ende]
            if z not in weg and not GATTUNG.match(z) and len(z) > 25]

    # Das Feld heisst datePublished, die Beschriftung lautet aber "Seite
    # aktualisiert am". Steht die Meldung auf der Monatsseite eines ANDEREN
    # Monats, war es eine spaetere Bearbeitung - dann ist das Datum als
    # Erscheinungstag unsicher. Erfunden wird trotzdem keines: Es bleibt das
    # einzige echte Datum, das die Quelle hergibt, nur gekennzeichnet.
    seiten_monat = eintrag.get("seiten_monat")
    unsicher = bool(seiten_monat and int(datum[5:7]) != seiten_monat)
    hinweis = ""
    if unsicher:
        hinweis = ("Die Kammer fuehrt diese Meldung unter Monat %02d, die Seite "
                   "selbst nennt den %s. Das ist vermutlich der Tag einer "
                   "spaeteren Bearbeitung." % (seiten_monat, datum))

    gattung = next((z for z in zeilen[:5] if GATTUNG.match(z)), "")
    return {
        "url": eintrag["url"],
        "datum": datum,
        "datum_ungenau": unsicher,
        "datum_hinweis": hinweis,
        "datum_quelle": "seite",
        "titel": eintrag["titel"],
        "dachzeile": eintrag["dachzeile"],
        "art_quelle": "presseeinladung" if "einladung" in gattung.lower()
                      else "pressemitteilung",
        "art_titel": gattung or "Pressemitteilung",
        "schlagworte": [],
        # Der Anrisstext der Kammer steht vorn, damit der Bau ihn als
        # Vorspann nehmen kann, ohne selbst zu kuerzen (KMS [L-0247]).
        "volltext": (eintrag["anriss"] + "\n" + "\n".join(text)).strip()
                    if eintrag["anriss"] else "\n".join(text).strip(),
        "quelle": "Handwerkskammer Cottbus",
        "ebene": "Brandenburg",
        "kennung": "cb-" + re.search(r"-7,0,(\d+)\.html", eintrag["url"]).group(1),
    }


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    jahr = sys.argv[1] if len(sys.argv) > 1 else str(datetime.date.today().year)
    print("Handwerkskammer Cottbus, Jahrgang", jahr)

    seiten = monatsseiten(jahr)
    print("Monatsseiten im Archiv:", len(seiten))
    if not seiten:
        print("HINWEIS: Fuer %s steht im Archiv noch keine Monatsseite." % jahr)

    eintraege = {}
    for u in seiten:
        s = hole(u, frisch=True)
        if not s:
            continue
        gefunden = anrisse_von(s)
        for e in gefunden.values():
            e["seiten_monat"] = monat_von(u)
        eintraege.update(gefunden)
        print("   %-58s %2d Meldungen" % (u.split("/")[-1][:58], len(gefunden)))

    ergebnis = []
    ohne_datum = 0
    for i, (kennung, e) in enumerate(sorted(eintraege.items()), 1):
        m = meldung_lesen(e)
        if not m:
            ohne_datum += 1
            continue
        if not m["datum"].startswith(jahr):
            continue
        if len(m["volltext"]) < 120:
            continue
        ergebnis.append(m)
        if i % 25 == 0:
            print("   ... %d von %d gelesen" % (i, len(eintraege)))

    ergebnis.sort(key=lambda x: x["datum"], reverse=True)
    ziel = os.path.join("daten", "hwk-cottbus-%s.json" % jahr)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=2)

    print()
    print("Meldungen auf den Monatsseiten:", len(eintraege))
    print("Uebernommen:", len(ergebnis))
    if ohne_datum:
        print("   ohne lesbares Datum uebersprungen:", ohne_datum)
    unsicher = sum(1 for x in ergebnis if x["datum_ungenau"])
    if unsicher:
        print("   davon mit unsicherem Datum (Monatsseite widerspricht):", unsicher)
    if ergebnis:
        print("   juengste:", ergebnis[0]["datum"], ergebnis[0]["titel"][:55])
        print("   aelteste:", ergebnis[-1]["datum"], ergebnis[-1]["titel"][:55])
    print("Geschrieben:", ziel)
