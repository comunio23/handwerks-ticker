# -*- coding: utf-8 -*-
"""
Sammelt die Veroeffentlichungen der Handwerkskammer Frankfurt (Oder) ein.

Diese Kammer laeuft auf WordPress und hat eine offene Schnittstelle. Darueber
kommen Datum, Titel, Anrisstext, Volltext und Kategorien als JSON - es wird
also NICHTS aus HTML geraten. Das ist der verlaesslichste der drei
Kammer-Abrufe.

Welche Kategorien eingesammelt werden, steht in daten/quellen.json. Vorgabe
ist "Medieninformationen" (die Pressemeldungen der Kammer selbst). Die
groessere Kategorie "Presse" enthaelt zusaetzlich Lehrberufeschauen und
Fotogalerien und ist deshalb abgeschaltet - sie laesst sich dort jederzeit
einschalten.

Die robots.txt der Kammer sperrt nichts ("Disallow:" ohne Wert).

Hoeflicher Abruf: eigener User-Agent, eine Sekunde Pause je Seitenabruf,
hoechstens 100 Beitraege pro Anfrage.

Aufruf:
    python scrape-hwk-ff.py            (nur das laufende Jahr)
    python scrape-hwk-ff.py 2025       (ein bestimmtes Jahr)
"""
import datetime
import html
import json
import os
import re
import sys
import time
import urllib.request

# Kontaktdaten gehoeren nicht in eine oeffentliche Datendatei
import ohne_kontaktdaten

UA = "Handwerks-Ticker/1.0 (Handwerksjunioren HWK Potsdam)"
PRO_SEITE = 100


def hole_json(url, versuche=3):
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                daten = json.loads(r.read().decode("utf-8"))
                kopf = dict(r.headers)
            time.sleep(1)
            return daten, kopf
        except Exception as e:
            if i == versuche - 1:
                print("  FEHLER bei", url, "->", e, file=sys.stderr)
                return None, {}
            time.sleep(2)


def nur_text(roh):
    """HTML der Schnittstelle zu lesbarem Text. Absaetze bleiben Absaetze."""
    t = re.sub(r"(?is)<(script|style|figure)\b.*?</\1>", " ", roh or "")
    t = re.sub(r"(?is)</(p|div|h[1-6]|li)>", "\n", t)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    t = t.replace(" ", " ")
    zeilen = [re.sub(r"[ \t]+", " ", z).strip() for z in t.split("\n")]
    return "\n".join(z for z in zeilen if z)


def quelle_laden():
    pfad = os.path.join("daten", "quellen.json")
    if not os.path.exists(pfad):
        sys.exit("daten/quellen.json fehlt.")
    quellen = json.load(open(pfad, encoding="utf-8"))
    if "hwk_frankfurt" not in quellen:
        sys.exit("In daten/quellen.json fehlt der Abschnitt 'hwk_frankfurt'.")
    return quellen["hwk_frankfurt"]


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    jahr = sys.argv[1] if len(sys.argv) > 1 else str(datetime.date.today().year)
    quelle = quelle_laden()
    basis = quelle["basis"].rstrip("/")
    aktiv = [k for k in quelle["kategorien"] if k.get("aktiv")]
    if not aktiv:
        sys.exit("Keine Kategorie aktiv - nichts zu holen.")

    print("Handwerkskammer Frankfurt (Oder), Jahrgang", jahr)
    print("Aktive Kategorien:", ", ".join(k["name"] for k in aktiv))

    kennungen = ",".join(str(k["id"]) for k in aktiv)
    namen = {k["id"]: k["name"] for k in quelle["kategorien"]}

    gefunden = {}
    seite = 1
    while True:
        url = ("%s/wp-json/wp/v2/posts?per_page=%d&page=%d&categories=%s"
               "&after=%s-01-01T00:00:00&before=%s-01-01T00:00:00"
               "&_fields=id,date,link,title,excerpt,content,categories"
               % (basis, PRO_SEITE, seite, kennungen, jahr, int(jahr) + 1))
        daten, kopf = hole_json(url)
        if not daten:
            break
        for p in daten:
            gefunden[p["id"]] = p
        gesamt = int(kopf.get("X-WP-Total", len(daten)) or 0)
        seiten = int(kopf.get("X-WP-TotalPages", 1) or 1)
        print("   Seite %d von %d (%d Beitraege insgesamt)" % (seite, seiten, gesamt))
        if seite >= seiten:
            break
        seite += 1

    ergebnis = []
    for p in gefunden.values():
        titel = html.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])).strip()
        volltext = nur_text(p["content"]["rendered"])
        anriss = nur_text(p["excerpt"]["rendered"])
        if not titel or len(volltext) < 120:
            continue
        schlagworte = [namen.get(k, "") for k in p.get("categories", [])]
        ergebnis.append({
            "url": p["link"],
            "datum": p["date"][:10],
            "datum_quelle": "seite",
            "titel": titel,
            "art_quelle": "pressemitteilung",
            "art_titel": "Medieninformation",
            "schlagworte": [s for s in schlagworte if s],
            # Der Anrisstext der Kammer steht als erste Zeile - so kann der
            # Bau ihn als Vorspann nehmen, ohne selbst zu kuerzen (KMS [L-0247]).
            "volltext": (anriss + "\n" + volltext) if anriss else volltext,
            "quelle": "Handwerkskammer Frankfurt (Oder)",
            "ebene": "Brandenburg",
            "kennung": "ff-%d" % p["id"],
        })

    ergebnis.sort(key=lambda x: x["datum"], reverse=True)
    # Vor dem Speichern: Durchwahlen und E-Mail-Adressen der
    # Pressestellen raus. Sie stehen im Original weiterhin da,
    # hier braucht sie niemand (siehe ohne_kontaktdaten.py).
    ohne_kontaktdaten.melden(ohne_kontaktdaten.saeubern(ergebnis))

    ziel = os.path.join("daten", "hwk-ff-%s.json" % jahr)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, indent=2)

    print()
    print("Uebernommen:", len(ergebnis))
    if ergebnis:
        print("   juengste:", ergebnis[0]["datum"], ergebnis[0]["titel"][:55])
        print("   aelteste:", ergebnis[-1]["datum"], ergebnis[-1]["titel"][:55])
    print("Geschrieben:", ziel)
