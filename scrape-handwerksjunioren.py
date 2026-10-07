# -*- coding: utf-8 -*-
"""
Sammelt die Veroeffentlichungen der Junioren des Handwerks e.V. ein
(handwerksjunioren.de, Bundesverband der Handwerksjunioren).

BESONDERHEIT DIESER QUELLE: Es gibt keinen Nachrichtenstrom. Die Seite ist
WordPress, hat aber genau einen Beitrag (von 2015) und vier Seiten - alle
Inhalte stehen auf der STARTSEITE, in zwei Abschnitten:

    <h1>PRESSE</h1>   -> je Meldung ein <h2>Datum: Titel</h2>, darunter der
                         Text in <h3>/<p>, bis zum naechsten <h2>
    <h1>TERMINE</h1>  -> abwechselnd <h2>Datum</h2> und <h2>Beschreibung</h2>

Daraus folgt dreierlei:
  1. Die Startseite MUSS bei jedem Lauf frisch geholt werden - sie ist
     Inhalt und Verzeichnis zugleich (KMS [L-0248]).
  2. Einzelne Meldungen haben keine eigene Adresse. Verlinkt wird deshalb
     der Seitenanker /#news bzw. /#termine.
  3. Die Kennung wird aus Datum und Titel gebildet. Wird ein Titel spaeter
     geaendert, gilt die Meldung einmalig als neu. Das ist der Preis dafuer,
     dass die Quelle keine Kennungen vergibt.

Erkannt wird ueber MUSTER, nicht ueber Position oder Schriftfarbe: Die Seite
faerbt Datumszeilen blau und Beschreibungen schwarz - darauf ist kein
Verlass, eine Umgestaltung wuerde den Abruf stillschweigend zerstoeren.

Hoeflicher Abruf: eigener User-Agent, eine Sekunde Pause, genau EIN Abruf
pro Lauf. Die robots.txt sperrt nur /wp-admin/ - das wird nicht angefasst.

Aufruf:
    python scrape-handwerksjunioren.py            (nur das laufende Jahr)
    python scrape-handwerksjunioren.py 2025       (ein bestimmtes Jahr)
"""
import datetime
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request

BASIS = "https://www.handwerksjunioren.de"
UA = "Handwerks-Ticker/1.0 (Handwerksjunioren HWK Potsdam)"

MONATE = {"januar": 1, "februar": 2, "maerz": 3, "märz": 3, "april": 4,
          "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
          "oktober": 10, "november": 11, "dezember": 12}

# "1. Oktober 2026", "3. + 4. November 2025", "26. Januar 2026, 16:30 - 17:30 Uhr"
DATUM_MUSTER = re.compile(
    r"^\s*(\d{1,2})\.\s*(?:[+&]\s*\d{1,2}\.\s*)?([A-Za-zÄÖÜäöü]+)\s+(\d{4})"
    r"\s*(?:,.*)?$")
# Dasselbe, aber mit Titel dahinter: "1. Oktober 2026: BILD Handwerksgipfel"
DATUM_TITEL_MUSTER = re.compile(
    r"^\s*(\d{1,2})\.\s*(?:[+&]\s*\d{1,2}\.\s*)?([A-Za-zÄÖÜäöü]+)\s+(\d{4})"
    r"\s*:\s*(.+)$")

# Zeilen, die zum Seitengeruest gehoeren und nicht zum Inhalt
GERUEST = re.compile(r"^(Fotos?\s*:|Foto\s*:|Bild\s*:|Quelle\s*:|v\.l\.n\.r\.)", re.I)

# Titel, die ein politisches Papier ankuendigen
PAPIER = re.compile(r"(Maßnahmenpapier|Positionspapier|Forderungspapier|"
                    r"Stellungnahme|Eckpunktepapier)", re.I)


def hole(url, versuche=3):
    """Holt die Seite. KEIN Cache: Diese eine Seite ist zugleich das
    Verzeichnis - aus dem Cache gelesen faende der Abgleich nie etwas Neues."""
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                seite = r.read().decode("utf-8", errors="replace")
            time.sleep(1)
            return seite
        except Exception as e:
            if i == versuche - 1:
                print("  FEHLER bei", url, "->", e, file=sys.stderr)
                return None
            time.sleep(2)


def sauber(roh):
    """HTML-Schnipsel zu lesbarem Text."""
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", roh)
    t = re.sub(r"(?is)<br\s*/?>", " ", t)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    t = t.replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()


def datum_lesen(text):
    """(iso, rest) aus einer Datums- oder Datum-Doppelpunkt-Titel-Zeile."""
    m = DATUM_TITEL_MUSTER.match(text)
    rest = ""
    if m:
        tag, monat, jahr, rest = m.group(1), m.group(2), m.group(3), m.group(4)
    else:
        m = DATUM_MUSTER.match(text)
        if not m:
            return None, ""
        tag, monat, jahr = m.group(1), m.group(2), m.group(3)
    nummer = MONATE.get(monat.lower())
    if not nummer:
        return None, ""
    try:
        iso = datetime.date(int(jahr), nummer, int(tag)).isoformat()
    except ValueError:
        return None, ""
    return iso, rest.strip()


def kennung_bilden(datum, titel):
    """Stabile Kennung ohne Quellen-ID: Datum plus entschaerfter Titel."""
    t = unicodedata.normalize("NFKD", titel.lower())
    t = (t.replace("ß", "ss").replace("ä", "ae")
          .replace("ö", "oe").replace("ü", "ue"))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    # Am Bindestrich kuerzen statt mitten im Wort - sonst heisst die Kennung
    # "...handwerkeri" und man sucht sie von Hand nie wieder.
    if len(t) > 60:
        t = t[:60].rsplit("-", 1)[0] if "-" in t[:60] else t[:60]
    return "%s-%s" % (datum, t.strip("-"))


def abschnitt(seite, von_marke, bis_marke):
    """Der Rohtext zwischen zwei Abschnittsmarken der Startseite."""
    a = seite.find(von_marke)
    if a < 0:
        return ""
    b = seite.find(bis_marke, a) if bis_marke else len(seite)
    return seite[a:b if b > 0 else len(seite)]


def presse_lesen(seite, bereich):
    """Der Abschnitt PRESSE: je <h2>Datum: Titel</h2> eine Meldung."""
    roh = abschnitt(seite, ">PRESSE<", 'id="termine"')
    if not roh:
        print("  HINWEIS: Abschnitt PRESSE nicht gefunden.", file=sys.stderr)
        return []

    # An den h2-Ueberschriften zerlegen; was dahinter kommt, ist der Text.
    stuecke = re.split(r"(?is)(<h2[^>]*>.*?</h2>)", roh)
    ergebnis = []
    offen = None
    for stueck in stuecke:
        if re.match(r"(?is)^<h2", stueck or ""):
            kopf = sauber(stueck)
            datum, titel = datum_lesen(kopf)
            if datum and titel:
                offen = {"datum": datum, "titel": titel, "text": []}
                ergebnis.append(offen)
            else:
                # Eine h2 ohne Datum gehoert zur laufenden Meldung (z.B. das
                # Bild eines Papiers) - sie beendet sie nicht.
                pass
            continue
        if offen is None or not stueck:
            continue
        for zeile in re.findall(r"(?is)<(?:h3|p)[^>]*>(.*?)</(?:h3|p)>", stueck):
            t = sauber(zeile)
            if t and not GERUEST.match(t) and len(t) > 12:
                offen["text"].append(t)

    fertig = []
    for e in ergebnis:
        papier = bool(PAPIER.search(e["titel"]))
        fertig.append({
            "url": BASIS + "/#news",
            "datum": e["datum"],
            "datum_quelle": "seite",
            "titel": e["titel"],
            "art_quelle": "papier" if papier else bereich["schluessel"],
            "art_titel": "Maßnahmenpapier" if papier else bereich["titel"],
            "schlagworte": [],
            "volltext": "\n".join(e["text"]).strip(),
            "quelle": "Junioren des Handwerks e.V.",
            "ebene": "Bund",
            "kennung": kennung_bilden(e["datum"], e["titel"]),
        })
    return fertig


def termine_lesen(seite, bereich):
    """Der Abschnitt TERMINE: abwechselnd <h2>Datum</h2>, <h2>Text</h2>."""
    roh = abschnitt(seite, ">TERMINE<", 'id="foerderer"')
    if not roh:
        print("  HINWEIS: Abschnitt TERMINE nicht gefunden.", file=sys.stderr)
        return []

    kopfzeilen = [sauber(h) for h in
                  re.findall(r"(?is)<h2[^>]*>(.*?)</h2>", roh)]
    ergebnis = []
    i = 0
    while i < len(kopfzeilen):
        datum, rest = datum_lesen(kopfzeilen[i])
        if not datum:
            i += 1
            continue
        # Der Titel steht in der naechsten Zeile - ausser er stand schon
        # hinter dem Doppelpunkt.
        beschreibung = rest
        if not beschreibung and i + 1 < len(kopfzeilen):
            naechste = kopfzeilen[i + 1]
            if not datum_lesen(naechste)[0]:
                beschreibung = naechste
                i += 1
        i += 1
        if not beschreibung:
            continue
        ergebnis.append({
            "url": BASIS + "/#termine",
            "datum": datum,
            "datum_quelle": "seite",
            "titel": beschreibung.rstrip("."),
            "art_quelle": bereich["schluessel"],
            "art_titel": bereich["titel"],
            "schlagworte": [],
            "volltext": beschreibung,
            "quelle": "Junioren des Handwerks e.V.",
            "ebene": "Bund",
            "kennung": kennung_bilden(datum, beschreibung),
        })
    return ergebnis


def bereiche_laden():
    pfad = os.path.join("daten", "quellen.json")
    if not os.path.exists(pfad):
        sys.exit("daten/quellen.json fehlt.")
    quellen = json.load(open(pfad, encoding="utf-8"))
    if "handwerksjunioren" not in quellen:
        sys.exit("In daten/quellen.json fehlt der Abschnitt 'handwerksjunioren'.")
    return quellen["handwerksjunioren"]


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    jahr = sys.argv[1] if len(sys.argv) > 1 else str(datetime.date.today().year)
    quelle = bereiche_laden()
    aktiv = [b for b in quelle["bereiche"] if b.get("aktiv")]
    print("Junioren des Handwerks, Jahrgang", jahr)
    print("Aktive Bereiche:", ", ".join(b["titel"] for b in aktiv) or "keine")

    seite = hole(quelle.get("startseite", BASIS + "/"))
    if not seite:
        sys.exit("Startseite der Handwerksjunioren nicht erreichbar.")

    heute = datetime.date.today().isoformat()
    alles = []
    uebersprungen = 0
    for b in aktiv:
        if b["schluessel"] in ("presse", "papier"):
            alles += presse_lesen(seite, b)
        elif b["schluessel"] == "termin":
            termine = termine_lesen(seite, b)
            # Fast jeder vergangene Termin hat im Abschnitt PRESSE schon
            # seinen Bericht - beides nebeneinander sieht aus wie doppelt.
            # Deshalb standardmaessig nur, was noch bevorsteht.
            if b.get("nur_kuenftige", True):
                vorher = len(termine)
                termine = [t for t in termine if t["datum"] >= heute]
                uebersprungen += vorher - len(termine)
            alles += termine
    if uebersprungen:
        print("   vergangene Termine uebersprungen (Bericht steht im Abschnitt "
              "PRESSE):", uebersprungen)

    # Dubletten koennen entstehen, wenn dieselbe Zeile in beiden Abschnitten
    # steht. Die Kennung entscheidet.
    gesehen = {}
    for x in alles:
        gesehen.setdefault(x["kennung"], x)
    alles = list(gesehen.values())

    im_jahr = [x for x in alles if (x["datum"] or "").startswith(jahr)]
    im_jahr.sort(key=lambda x: x["datum"], reverse=True)

    ziel = os.path.join("daten", "handwerksjunioren-%s.json" % jahr)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(im_jahr, f, ensure_ascii=False, indent=2)

    import collections
    verteilung = collections.Counter(x["art_quelle"] for x in im_jahr)
    ohne_text = sum(1 for x in im_jahr if len(x["volltext"]) < 40)
    print()
    print("Gefunden insgesamt:", len(alles))
    print("Davon im Jahrgang %s: %d" % (jahr, len(im_jahr)))
    for k, n in verteilung.most_common():
        print("   %-16s %3d" % (k, n))
    if ohne_text:
        print("   davon ohne eigenen Text auf der Seite:", ohne_text)
    print("Geschrieben:", ziel)
