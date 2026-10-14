# -*- coding: utf-8 -*-
"""
Sammelt die Pressemitteilungen des brandenburgischen Wirtschaftsministeriums
ein - der Gegenseite.

Das Ministerium fuer Wirtschaft, Energie, Klimaschutz und Europa (MWEKE) ist
der Adressat vieler Handwerksforderungen. Wer wissen will, ob eine Forderung
beantwortet wurde, muss auch hoeren, was das Ministerium sagt.

Die Seite laeuft im Landes-CMS. Eigenheiten:

  * Die Domain wechselt je nach Zuschnitt des Hauses (mwae, mwaek, mweke) -
    alle zeigen auf dieselbe Installation. Ein Verweis wird deshalb immer auf
    die in quellen.json hinterlegte Basis umgeschrieben, sonst stuende
    dieselbe Meldung unter zwei Adressen in den Daten.
  * Die Presseliste zeigt IMMER NUR 15 Meldungen und kennt kein Blaettern.
    Dafuer gibt es Rubriken ("Handel und Handwerk", "Ausbildung, Arbeit" ...),
    die je 15 eigene Meldungen fuehren - bei schmalen Rubriken reicht das
    Jahre zurueck. Gesammelt wird deshalb ueber die Rubriken, nicht ueber die
    Gesamtliste. Welche aktiv sind, steht in daten/quellen.json.
  * Das Datum steht in der Liste (TT.MM.JJJJ) UND in der Meldung selbst
    ("Potsdam, 1. Oktober 2026"). Beide werden verglichen; weichen sie ab,
    wird die Meldung als datum_ungenau gekennzeichnet statt stillschweigend
    einem Tag zugeordnet.
  * Eine robots.txt gibt es nicht (HTTP 404), es ist also nichts gesperrt.
    Der Abruf bleibt trotzdem hoeflich: eigener User-Agent, eine Sekunde
    Pause, lokaler Cache. Rubrikseiten werden frisch geholt, Meldungen nicht.

Aufruf:
    python scrape-mweke.py              (nur das laufende Jahr)
    python scrape-mweke.py 2025         (ein bestimmtes Jahr)
"""
import datetime
import html as html_modul
import io
import json
import os
import re
import sys
import time
import urllib.request

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UA = "Handwerks-Ticker/1.0 (Handwerksjunioren HWK Potsdam)"
CACHE = os.path.join("daten", "cache-mweke")
QUELLEN = os.path.join("daten", "quellen.json")

# Eine Zeile der Presseliste: Datum | Verweis, Titel und (meist) Untertitel
LISTENZEILE = re.compile(
    r'<td class="col-xs-4">\s*(\d{2})\.(\d{2})\.(\d{4})\s*</td>\s*'
    r'<td class="col-xs-8">\s*<a href="([^"]+)">\s*<strong>(.*?)</strong>\s*'
    r'(?:<br\s*/?>(.*?))?</a>', re.S)

# "Potsdam, 1. Oktober 2026" am Anfang der Meldung
DATUM_IM_TEXT = re.compile(r"\b(\d{1,2})\.\s*([A-Za-zÄÖÜäöü]+)\s+(\d{4})\b")
MONATE = {"januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
          "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
          "oktober": 10, "november": 11, "dezember": 12}

FUSS = re.compile(r"^(Pressekontakt|Pressestelle|Kontakt$|Weitere Informationen$|"
                  r"Tel\.|Telefon|E-Mail|Hinweis für die Redaktion)", re.I)


def hole(url, frisch=False, versuche=3):
    """Eine Seite holen. Rubrikseiten frisch, Meldungen aus dem Cache."""
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
                print("  FEHLER bei %s -> %s" % (url, e), file=sys.stderr)
                return None
            time.sleep(2)


def zeilen_von(roh):
    t = re.sub(r"(?is)<(script|style|nav|figure|form)\b.*?</\1>", " ", roh)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = html_modul.unescape(re.sub(r"(?s)<[^>]+>", "\n", t))
    t = t.replace(" ", " ")
    return [re.sub(r"[ \t]+", " ", z).strip() for z in t.split("\n") if z.strip()]


def einstellungen():
    if not os.path.exists(QUELLEN):
        sys.exit("daten/quellen.json fehlt.")
    q = json.load(open(QUELLEN, encoding="utf-8")).get("wirtschaftsministerium")
    if not q:
        sys.exit("In daten/quellen.json fehlt der Abschnitt "
                 "'wirtschaftsministerium'.")
    return q


def liste_lesen(q, rubrik, jahr):
    """Eine Rubrikseite auslesen. Gibt die Meldungen des Jahrgangs zurueck."""
    url = q["basis"] + q["liste"]
    if rubrik.get("sv"):
        url += "?sv=" + rubrik["sv"]
    seite = hole(url, frisch=True)
    if not seite:
        return []
    gefunden = []
    for tag, monat, j, weg, titel, unter in LISTENZEILE.findall(seite):
        if j != str(jahr):
            continue
        kennung = re.search(r"id=(\d+)", weg)
        if not kennung:
            continue
        gefunden.append({
            # Immer auf die hinterlegte Basis umschreiben: Dieselbe Meldung
            # ist sonst unter mwae/mwaek/mweke dreimal in den Daten.
            "url": q["basis"] + weg if weg.startswith("/") else weg,
            "kennung": "mweke-" + kennung.group(1),
            "datum": "%s-%s-%s" % (j, monat, tag),
            "titel": " ".join(html_modul.unescape(
                re.sub(r"<[^>]+>", "", titel)).split()),
            "untertitel": " ".join(html_modul.unescape(
                re.sub(r"<[^>]+>", "", unter or "")).split()),
            "rubrik": rubrik["titel"],
        })
    return gefunden


def meldung_lesen(eintrag):
    """Volltext der Meldung holen und das Datum gegenpruefen."""
    seite = hole(eintrag["url"])
    if not seite:
        return None
    m = re.search(r"(?is)<article\b.*?</article>", seite)
    if not m:
        return None
    zeilen = zeilen_von(m.group(0))

    # Alles ab dem Pressekontakt gehoert nicht mehr zur Meldung
    ende = len(zeilen)
    for i, z in enumerate(zeilen):
        if FUSS.match(z):
            ende = i
            break
    weg = {eintrag["titel"], eintrag["untertitel"]}
    text = [z for z in zeilen[:ende] if z not in weg and len(z) > 25]

    # Gegenprobe: Die Meldung nennt ihr Datum meist selbst ("Potsdam,
    # 1. Oktober 2026"). Weicht es von der Liste ab, wird das vermerkt -
    # erfunden wird keines, es bleibt beim Datum der Liste.
    unsicher, hinweis = False, ""
    treffer = DATUM_IM_TEXT.search(" ".join(text[:2]))
    if treffer:
        nummer = MONATE.get(treffer.group(2).lower())
        if nummer:
            try:
                im_text = datetime.date(int(treffer.group(3)), nummer,
                                        int(treffer.group(1))).isoformat()
                if im_text != eintrag["datum"]:
                    unsicher = True
                    hinweis = ("Die Presseliste fuehrt diese Meldung unter dem "
                               "%s, die Meldung selbst nennt den %s."
                               % (eintrag["datum"], im_text))
            except ValueError:
                pass

    return {
        "url": eintrag["url"],
        "datum": eintrag["datum"],
        "datum_ungenau": unsicher,
        "datum_hinweis": hinweis,
        "datum_quelle": "liste",
        "titel": eintrag["titel"],
        "dachzeile": eintrag["untertitel"],
        "art_quelle": "pressemitteilung",
        "art_titel": "Pressemitteilung",
        # Die Rubriken des Ministeriums sind brauchbare Schlagworte fuer die
        # Themenerkennung des Baus.
        "schlagworte": sorted(eintrag["rubriken"]),
        # Der Untertitel vorn, damit der Bau ihn als Vorspann nehmen kann,
        # ohne selbst zu kuerzen (KMS [L-0247]).
        "volltext": (eintrag["untertitel"] + "\n" + "\n".join(text)).strip()
                    if eintrag["untertitel"] else "\n".join(text).strip(),
        "quelle": "Ministerium fuer Wirtschaft, Energie, Klimaschutz und Europa",
        "ebene": "Brandenburg",
        "seite": "Landesregierung",
        "kennung": eintrag["kennung"],
    }


def main():
    jahr = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() \
        else datetime.date.today().year
    q = einstellungen()
    rubriken = [r for r in q["rubriken"] if r.get("aktiv")]
    print("Wirtschaftsministerium Brandenburg, Jahrgang %d" % jahr)
    print("Aktive Rubriken: %s" % ", ".join(r["titel"] for r in rubriken))

    # Dieselbe Meldung steht oft in mehreren Rubriken. Sie wird einmal
    # gefuehrt, merkt sich aber alle Rubriken als Schlagworte.
    gesammelt = {}
    for rubrik in rubriken:
        treffer = liste_lesen(q, rubrik, jahr)
        print("   %-24s %2d aus %d" % (rubrik["titel"], len(treffer), jahr))
        for t in treffer:
            vorhanden = gesammelt.get(t["kennung"])
            if vorhanden:
                vorhanden["rubriken"].add(t["rubrik"])
            else:
                t["rubriken"] = {t["rubrik"]}
                gesammelt[t["kennung"]] = t

    if not gesammelt:
        print("Keine Meldungen gefunden - Aufbau der Seite pruefen.")
        return 2

    fertig = []
    for eintrag in sorted(gesammelt.values(), key=lambda x: x["datum"], reverse=True):
        meldung = meldung_lesen(eintrag)
        if meldung:
            fertig.append(meldung)

    unsicher = sum(1 for m in fertig if m["datum_ungenau"])
    print("Uebernommen: %d" % len(fertig))
    if unsicher:
        print("   davon mit abweichendem Datum in der Meldung: %d" % unsicher)
    if fertig:
        print("   neueste: %s %s" % (fertig[0]["datum"], fertig[0]["titel"][:60]))

    ziel = os.path.join("daten", "mweke-%d.json" % jahr)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(fertig, f, ensure_ascii=False, indent=1)
    print("Geschrieben: %s" % ziel)
    return 0


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
