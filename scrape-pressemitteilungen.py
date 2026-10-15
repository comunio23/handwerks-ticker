# -*- coding: utf-8 -*-
"""
Sammelt die Pressemitteilungen der Handwerkskammer Potsdam ein.

Ablauf:
  1. Jahresuebersicht holen (die URL enthaelt die Jahreszahl!)
  2. jede verlinkte Artikelseite holen und Kopfzeile, Titel und Volltext trennen
  3. fehlende Datumsangaben aus der sitemap.xml (lastmod) ergaenzen
  4. alles als JSON nach daten/meldungen-<jahr>.json schreiben

Hoeflicher Abruf: eigener User-Agent, 1 Sekunde Pause nach jedem echten Abruf,
lokaler Cache unter daten/cache/. Nur /artikel/-Seiten und die sitemap.xml -
beides ist laut robots.txt ausdruecklich erlaubt. /downloads/ wird bewusst
NICHT angefasst, denn diesen Pfad sperrt die robots.txt.

Aufruf:
    python scrape-pressemitteilungen.py
    python scrape-pressemitteilungen.py <URL-der-Jahresuebersicht>
"""
import json
import re
import html
import sys
import time
import os
import urllib.request

# Kontaktdaten gehoeren nicht in eine oeffentliche Datendatei
import ohne_kontaktdaten

BASIS = "https://www.hwk-potsdam.de"
UA = "Handwerks-Ticker/1.0 (Handwerksjunioren HWK Potsdam)"
CACHE = os.path.join("daten", "cache")

UMLAUTE = "ÄÖÜäöüß"

MONATE = {"Januar": 1, "Februar": 2, "März": 3, "Maerz": 3, "April": 4,
          "Mai": 5, "Juni": 6, "Juli": 7, "August": 8, "September": 9,
          "Oktober": 10, "November": 11, "Dezember": 12}

DATUM_MUSTER = re.compile(r"vom\s+(\d{1,2})\.\s*([A-Za-z" + UMLAUTE + r"]+)\s+(\d{4})")
NUMMER_MUSTER = re.compile(r"Presse(?:information|einladung)\s+Nr\.?:?\s*(\d+)")

# Kopfzeile: "Presseinformation Nr. 59 vom ...", aber auch
# "Presseeinladung Nr. 16 vom ..." und
# "Gemeinsame Presseinformation der Landesregierung ..." ohne Nummer und ohne Datum
KOPF_MUSTER = re.compile(
    r"^(Gemeinsame\s+)?Presse(information|einladung|mitteilung|meldung)\b", re.I)
FUSS_MUSTER = re.compile(r"^(Pressesprecher|Tel\. \+49|Mobil \+49|Ansprechpartner|Inhalt$)")

# Nennt eine gemeinsame Kopfzeile viele Absender, wird sie zu lang und das Datum
# rutscht in die naechste Zeile: "... und Bundesverband der Systemgastronomie (BdS)"
# / "vom 8. September 2026". Diese Fortsetzung ist nie der Titel.
KOPF_FORTSETZUNG = re.compile(r"^vom\s+\d{1,2}\.\s*\w+\s*\d{4}\.?$", re.I)

# Bildnachweis-Zeile ganz oben, z.B. "AdobeStock_lev dolgachov" oder "Tom - Fotolia"
BILD_MUSTER = re.compile(r"(AdobeStock|Adobe Stock|Fotolia|HWK Potsdam/|"
                         r"Handwerkskammer Potsdam/|Phovoir|stockpics|Pixabay|Unsplash)", re.I)


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
                roh = r.read()
            seite = roh.decode("utf-8", errors="replace")
            open(pfad, "w", encoding="utf-8").write(seite)
            time.sleep(1)
            return seite
        except Exception as e:
            if i == versuche - 1:
                print("  FEHLER bei", url, "->", e, file=sys.stderr)
                return None
            time.sleep(2)


def nur_text(fragment):
    """HTML-Fragment zu lesbarem Text; die Zeilenstruktur bleibt erhalten."""
    fragment = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?is)<br\s*/?>", "\n", fragment)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", "\n", fragment))
    return "\n".join(z.strip() for z in t.split("\n") if z.strip())


def datum_und_nummer(text):
    """Aus 'Presseinformation Nr. 59 vom 31. Juli 2026' wird ('2026-07-31', '59')."""
    nr = None
    m = NUMMER_MUSTER.search(text)
    if m:
        nr = m.group(1)
    datum = None
    m = DATUM_MUSTER.search(text)
    if m and m.group(2) in MONATE:
        datum = "%s-%02d-%02d" % (m.group(3), MONATE[m.group(2)], int(m.group(1)))
    return datum, nr


def artikel_id(url):
    """Aus '...-9,735,6853.html' wird '6853'. Die mittlere Zahl ist nur der
    Navigationspfad und unterscheidet sich zwischen Sitemap und Pressebereich -
    die letzte Zahl bezeichnet den Artikel selbst."""
    m = re.search(r"-\d+,\d+,(\d+)\.html", url)
    return m.group(1) if m else None


def sitemap_daten():
    """Artikel-ID -> lastmod aus der sitemap.xml.
    Notnagel fuer Meldungen, die im Text gar kein Datum tragen."""
    seite = hole(BASIS + "/sitemap.xml")
    if not seite:
        return {}
    paare = re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", seite)
    treffer = {}
    for u, d in paare:
        kennung = artikel_id(u.strip())
        if kennung:
            treffer[kennung] = d.strip()[:10]
    return treffer


def uebersicht_einsammeln(url_uebersicht):
    """Liest die Jahresuebersicht und liefert die Links aller Meldungen."""
    seite = hole(url_uebersicht)
    if not seite:
        sys.exit("Uebersichtsseite nicht erreichbar.")
    kacheln = re.findall(
        r'<div class="teaser-tile teaser-box".*?'
        r'(?=<div class="teaser-tile teaser-box"|<footer|$)', seite, re.S)
    treffer = []
    for k in kacheln:
        m = re.search(r'href="([^"]+)"', k)
        if not m:
            continue
        link = m.group(1)
        if "/artikel/" not in link:
            continue
        if not link.startswith("http"):
            link = BASIS + link
        roh = re.sub(r"\s+", " ", nur_text(k).replace("\n", " ")).strip()
        roh = roh.replace(" mehr lesen", "")
        datum, nr = datum_und_nummer(roh)
        treffer.append({"url": link, "datum": datum, "nummer": nr, "kachel_roh": roh})
    return treffer


def kopf_finden(zeilen):
    """Liefert (kopfzeile, dachzeile, titel, index_ab_dem_der_fliesstext_beginnt)."""
    # Fall 1: es gibt eine Presseinformations-Kopfzeile
    for i, z in enumerate(zeilen[:10]):
        if KOPF_MUSTER.match(z):
            kopf, j = z, i + 1
            # Umgebrochene Kopfzeile: die Datumszeile gehoert noch zum Kopf
            while j < len(zeilen) and KOPF_FORTSETZUNG.match(zeilen[j]):
                kopf += " " + zeilen[j]
                j += 1
            titel = zeilen[j] if j < len(zeilen) else ""
            return kopf, "", titel, j + 1

    # Fall 2: keine Kopfzeile. Zuerst den Bildnachweis ueberspringen, dann eine
    # moegliche Dachzeile ("Brandenburger Handwerk warnt:"), dann der Titel.
    i = 0
    if i < len(zeilen) and BILD_MUSTER.search(zeilen[i]) and len(zeilen[i]) < 60:
        i += 1
    dachzeile = ""
    if i < len(zeilen) and zeilen[i].endswith(":") and len(zeilen[i]) < 80:
        dachzeile = zeilen[i]
        i += 1
    titel = zeilen[i] if i < len(zeilen) else ""
    return "", dachzeile, titel, i + 1


def artikel_holen(eintrag, lastmod):
    """Holt eine Artikelseite und zerlegt sie in Kopf, Titel und Volltext."""
    seite = hole(eintrag["url"])
    if not seite:
        return None
    m = re.search(r'<div class="container content".*?(?=<footer|</body)', seite, re.S)
    zeilen = nur_text(m.group(0) if m else seite).split("\n")

    kopf, dachzeile, titel, start = kopf_finden(zeilen)

    ende = len(zeilen)
    for i in range(start, len(zeilen)):
        if FUSS_MUSTER.match(zeilen[i]):
            ende = i
            break
    # Der Name der Pressesprecherin steht eine Zeile ueber ihrer Funktion
    if ende < len(zeilen) and zeilen[ende].startswith("Pressesprecher") and ende > start:
        ende -= 1

    fliesstext = "\n".join(zeilen[start:ende]).strip()

    datum, nr = datum_und_nummer(kopf) if kopf else (None, None)
    datum_quelle = "kopfzeile"
    if not datum:
        datum, datum_quelle = eintrag["datum"], "uebersicht"
    if not datum:
        datum, datum_quelle = lastmod.get(artikel_id(eintrag["url"])), "sitemap"
    if not datum:
        datum_quelle = "unbekannt"

    return {
        "nummer": nr or eintrag["nummer"],
        "datum": datum,
        "datum_quelle": datum_quelle,
        "kopfzeile": kopf,
        "dachzeile": dachzeile,
        "titel": titel or eintrag["kachel_roh"][:160],
        "volltext": fliesstext,
        "url": eintrag["url"],
        "quelle": "Handwerkskammer Potsdam",
    }


if __name__ == "__main__":
    uebersicht = sys.argv[1] if len(sys.argv) > 1 else \
        BASIS + "/artikel/pressemitteilungen-2026-9,735,6713.html"
    jahr = re.search(r"(\d{4})", uebersicht).group(1)

    print("Uebersicht:", uebersicht)
    liste = uebersicht_einsammeln(uebersicht)
    print("Gefundene Meldungen:", len(liste))
    print("Sitemap laden ...")
    lastmod = sitemap_daten()
    print("Sitemap-Eintraege:", len(lastmod))

    ergebnis = []
    for i, e in enumerate(liste, 1):
        a = artikel_holen(e, lastmod)
        if a:
            ergebnis.append(a)
            print("  [%2d/%d] %s | %s" % (i, len(liste), a["datum"], a["titel"][:60]))

    # Letzter Ausweg fuer Meldungen ohne jedes Datum: Die Uebersichtsseite ist
    # chronologisch sortiert, also uebernehmen wir das Datum des Vorgaengers.
    # Das ist eine Ableitung, keine Angabe der Quelle - deshalb gekennzeichnet.
    for i, a in enumerate(ergebnis):
        if a["datum"]:
            continue
        nachbar = next((ergebnis[j]["datum"] for j in range(i - 1, -1, -1)
                        if ergebnis[j]["datum"]), None)
        if not nachbar:
            nachbar = next((ergebnis[j]["datum"] for j in range(i + 1, len(ergebnis))
                            if ergebnis[j]["datum"]), None)
        if nachbar:
            a["datum"] = nachbar
            a["datum_quelle"] = "eingeordnet"
            print("  Hinweis: '%s' hat kein Datum in der Quelle - "
                  "aus der Reihenfolge auf %s eingeordnet." % (a["titel"][:45], nachbar))

    ergebnis.sort(key=lambda x: (x["datum"] or ""), reverse=True)
    # Vor dem Speichern: Durchwahlen und E-Mail-Adressen der
    # Pressestellen raus. Sie stehen im Original weiterhin da,
    # hier braucht sie niemand (siehe ohne_kontaktdaten.py).
    ohne_kontaktdaten.melden(ohne_kontaktdaten.saeubern(ergebnis))

    ziel = os.path.join("daten", "meldungen-%s.json" % jahr)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=2)
    print("Geschrieben:", ziel, "-", len(ergebnis), "Meldungen")
