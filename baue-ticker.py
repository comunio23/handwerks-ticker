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
ERSTBESTAND = "erstbestand"   # Marke fuer alles, was beim ersten Lauf schon da war

MIN_ZITAT = 120     # kuerzere Anfuehrungen sind meist Projekt- oder Titelnamen
MAX_ZITAT = 2000    # Statements der Praesidenten sind oft ein ganzer Absatz
ANZEIGE_ZITAT = 320  # so lang darf das Zitat auf der Karte hoechstens werden

ZITAT_MUSTER = re.compile(r"[„“\"]([^“”\"]{%d,%d})[“”\"]" % (MIN_ZITAT, MAX_ZITAT))
SATZ_ENDE = re.compile(r"[.!?](?=\s|$)")


def artikel_id(url):
    m = re.search(r"-\d+,\d+,(\d+)\.html", url)
    return m.group(1) if m else None


def absender_bestimmen(meldung):
    """Wer spricht? Viele Meldungen auf hwk-potsdam.de stammen nicht von der
    Kammer Potsdam allein, sondern vom Brandenburgischen Handwerkskammertag -
    dem Zusammenschluss der Kammern Cottbus, Frankfurt (Oder) und Potsdam mit
    Federfuehrung Potsdam. Das ist politisch der Unterschied zwischen einer
    regionalen Stimme und der Stimme des Landeshandwerks."""
    kopf = meldung.get("kopfzeile", "")
    text = meldung["volltext"]
    anfang = text[:400]

    if kopf.lower().startswith("gemeinsame presse"):
        return "Gemeinsam mit Partnern"
    if "Handwerkskammertag" in kopf:
        return "Handwerkskammertag Brandenburg"
    # Die Ortszeile nennt bei Landesmeldungen alle drei Kammerstaedte
    if re.search(r"(Cottbus|Frankfurt \(Oder\))[/ ].*Potsdam|Potsdam/\s*Cottbus", anfang):
        return "Handwerkskammertag Brandenburg"
    if "Handwerkskammertag" in anfang:
        return "Handwerkskammertag Brandenburg"
    return "Handwerkskammer Potsdam"


# Die Schlagworte, die der ZDH selbst an seine Meldungen haengt, auf unsere
# Themen abbilden. Damit bekommt auch eine Meldung ohne Redaktionseintrag
# sofort ein sinnvolles Thema - ohne dass jemand etwas erfinden muss.
SCHLAGWORT_THEMA = [
    ("Steuern & Abgaben",
     ["steuer", "grundsteuer", "lohnsteuer", "umsatzsteuer", "erbschaft"]),
    ("Sozialabgaben & Rente",
     ["sozialversicherung", "rente", "kranken", "pflege", "lohnzusatzkosten"]),
    ("Arbeitszeit & Arbeitsrecht",
     ["arbeitszeit", "arbeitsrecht", "gesundheitsschutz", "mindestlohn"]),
    ("Ausbildung & Nachwuchs",
     ["ausbildung", "berufsbildung", "bildungspolitik", "bafög", "bafoeg",
      "euroskills", "weiterbildung", "allianz für aus", "azubi", "lehrstelle"]),
    ("Personal & Fachkräfte",
     ["fachkräfte", "fachkraft", "migrationshintergrund", "demografie",
      "arbeitslosen", "arbeitsmarkt"]),
    ("Energie & Sprit",
     ["energiepreise", "stromsteuer", "energie- und"]),
    ("Aufträge & Vergabe",
     ["vergabe", "ausschreibung"]),
    ("Betrieb & Nachfolge",
     ["betriebsübergabe", "nachfolge", "gründung", "existenzgründ"]),
    ("Bauen & Sanieren",
     ["gebäude", "baurecht", "infrastruktur", "wohnungsbau", "klimapolitik",
      "bauwirtschaft"]),
    ("Entbürokratisierung",
     ["bürokratie", "bürokratische", "e-rechnung", "recht auf reparatur",
      "digitaler omnibus", "bonpflicht", "entlastung", "sonntagsback"]),
    ("Wirtschaftslage",
     ["wettbewerbsfähigkeit", "investitionen", "strukturpolitik", "strukturwandel",
      "nachhaltige finanzierung", "konjunktur", "binnenmarkt"]),
    ("Ehrungen & Termine",
     ["handwerksmesse", "handwerksgeschichte", "kulturhandwerk", "kirche",
      "spitzengespräch", "preis"]),
]


def thema_aus_schlagworten(schlagworte, titel=""):
    """Thema zuerst aus den Schlagworten der Quelle, dann ersatzweise aus dem
    Titel. Manche Meldungen tragen gar keine Schlagworte - dann ist der Titel
    die naechstbeste Grundlage, die immer noch aus der Quelle stammt."""
    for text in (" ".join(schlagworte).lower(), (titel or "").lower()):
        if not text.strip():
            continue
        for thema, worte in SCHLAGWORT_THEMA:
            if any(w in text for w in worte):
                return thema
    return None


def zdh_laden():
    """Die bundesweiten ZDH-Meldungen in dieselbe Form bringen wie die
    Kammer-Meldungen. Bewusst NUR Pressemitteilungen mit echtem Datum von der
    Seite - die Positionspapiere tragen kein Erscheinungsdatum, und das
    lastmod der Sitemap ist bei 63 von 64 der Tag der Systemumstellung."""
    pfad_daten = "daten/zdh-%s.json" % JAHR
    pfad_redaktion = "daten/redaktion-zdh-%s.json" % JAHR
    if not (os.path.exists(pfad_daten) and os.path.exists(pfad_redaktion)):
        print("Hinweis: keine ZDH-Daten gefunden - der Ticker bleibt bei der Kammer.")
        return []

    roh = json.load(open(pfad_daten, encoding="utf-8"))
    redaktion = json.load(open(pfad_redaktion, encoding="utf-8"))["eintraege"]

    fertig = []
    ohne = 0
    for x in roh:
        # Positionspapiere bleiben draussen: kein Erscheinungsdatum (KMS [D-0182])
        if x["art_quelle"] == "position" or x["datum_quelle"] != "seite":
            continue
        kennung = x["url"].rstrip("/").split("/")[-1]
        r = redaktion.get(kennung)
        if not r:
            # Kein Redaktionseintrag - dann sprechen die Quelle selbst und ihre
            # eigenen Schlagworte. Der Vorspann des ZDH ist dessen eigener
            # Anrisstext, keine Zusammenfassung von uns. So faellt nichts unter
            # den Tisch und trotzdem wird nichts erfunden.
            ohne += 1
            vorspann = (x["volltext"].splitlines() or [""])[0].strip()
            r = {
                "art": "politik" if x["art_quelle"] != "rede" else "bericht",
                "thema": thema_aus_schlagworten(x.get("schlagworte", []),
                                                x.get("titel", ""))
                         or "Noch nicht eingeordnet",
                "dreizeiler": vorspann,
                "quelle_eigen": True,
            }
        fertig.append({
            "id": "zdh-" + kennung,
            "datum": x["datum"],
            "datum_ungenau": False,
            "nummer": None,
            "titel": x["titel"],
            "url": x["url"],
            "art": r["art"],
            "thema": r["thema"],
            "thema2": r.get("thema2"),
            "absender": "Zentralverband des Deutschen Handwerks",
            "ebene": "Bund",
            # Die Ueberschrift des ZDH wird unveraendert uebernommen - sie ist
            # praezise formuliert, eine eigene Fassung koennte nur verzerren.
            "schlagzeile": x["titel"],
            "dreizeiler": r["dreizeiler"],
            "unredigiert": bool(r.get("quelle_eigen")),
            "quelle_eigen": bool(r.get("quelle_eigen")),
            "gattung": x.get("art_titel", ""),
            "zitat": None,
        })
    if ohne:
        print("   davon mit dem eigenen Anrisstext des ZDH statt Dreizeiler:", ohne)
    return fertig


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

    # Welche Meldungen kannten wir beim letzten Lauf? Alles, was neu dazukommt,
    # bekommt das heutige Datum und wird im Ticker oben angepinnt.
    bekannt_pfad = "daten/bekannt.json"
    bekannt = (json.load(open(bekannt_pfad, encoding="utf-8"))
               if os.path.exists(bekannt_pfad) else {})
    erster_lauf = not bekannt
    heute = datetime.date.today().isoformat()

    # Welche QUELLEN kennen wir schon? Kommt eine neue dazu, ist ihr ganzer
    # Bestand Grundbestand - sonst stuenden beim naechsten Aufruf hundert
    # Meldungen als "neu" oben, nur weil eine Quelle angeschlossen wurde.
    quellen_pfad = "daten/bekannte-quellen.json"
    bekannte_quellen = set(json.load(open(quellen_pfad, encoding="utf-8"))
                           if os.path.exists(quellen_pfad) else [])

    fertig = []
    ohne_redaktion = []
    zitate = 0

    for m in meldungen:
        kennung = artikel_id(m["url"])
        r = redaktion.get(kennung)
        if not r:
            # Neue Meldung, noch nicht redigiert. Sie faellt nicht unter den Tisch:
            # gezeigt wird der Originaltitel der Kammer - das ist deren eigene
            # Formulierung, keine unbelegte Zusammenfassung (siehe KMS [D-0170]).
            ohne_redaktion.append((kennung, m["titel"][:60]))
            r = {"art": "unsortiert", "thema": "Noch nicht eingeordnet",
                 "schlagzeile": m["titel"], "dreizeiler": "", "unredigiert": True}

        zitat = None
        if r.get("zitat_zeigen"):
            zitat = zitat_finden(m["volltext"])
            if zitat:
                zitate += 1
            else:
                print("  Hinweis: kein Zitat gefunden fuer %s (%s)"
                      % (kennung, m["titel"][:45]))

        # Vermerkt wird der TAG DES ABGLEICHS, an dem die Meldung zum ersten Mal
        # auftauchte - nicht ihr Erscheinungsdatum. Der Grundbestand des ersten
        # Laufs bekommt eine eigene Marke, sonst gaelte die juengste Meldung des
        # Jahrgangs faelschlich als Neuzugang.
        if kennung not in bekannt:
            neue_quelle = "hwk" not in bekannte_quellen
            bekannt[kennung] = ERSTBESTAND if (erster_lauf or neue_quelle) else heute

        fertig.append({
            "id": kennung,
            "datum": m["datum"],
            "datum_ungenau": m["datum_quelle"] == "eingeordnet",
            "nummer": m["nummer"],
            "titel": m["titel"],
            "url": m["url"],
            "art": r["art"],
            "thema": r["thema"],
            "thema2": r.get("thema2"),
            "absender": absender_bestimmen(m),
            "schlagzeile": r["schlagzeile"],
            "dreizeiler": r["dreizeiler"],
            "unredigiert": bool(r.get("unredigiert")),
            "zuerst_gesehen": bekannt[kennung],
            "zitat": zitat,
        })

    for x in fertig:
        x["ebene"] = "Brandenburg"

    zdh = zdh_laden()
    zdh_neu_angeschlossen = zdh and "zdh" not in bekannte_quellen
    if zdh_neu_angeschlossen:
        print("   ZDH ist neu angeschlossen - der Bestand zaehlt als Grundbestand,")
        print("   nicht als Neuzugang. Ab dem naechsten Abgleich faellt Neues auf.")
    for x in zdh:
        if x["id"] not in bekannt:
            bekannt[x["id"]] = (ERSTBESTAND
                                if (erster_lauf or zdh_neu_angeschlossen) else heute)
        x["zuerst_gesehen"] = bekannt[x["id"]]
    fertig.extend(zdh)
    fertig.sort(key=lambda x: (x["datum"] or ""), reverse=True)
    print("Bundesebene (ZDH):", len(zdh), "Meldungen")

    # "Neu" heisst: beim juengsten Abgleich dazugekommen. Der Grundbestand
    # zaehlt nie mit.
    abgleichstage = [v for v in bekannt.values() if v != ERSTBESTAND]
    neuestes = max(abgleichstage) if abgleichstage else None
    neu_ids = [k for k, v in bekannt.items() if v == neuestes] if neuestes else []
    for x in fertig:
        x["neu"] = x["id"] in neu_ids

    json.dump(bekannt, open(bekannt_pfad, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, sort_keys=True)

    bekannte_quellen.add("hwk")
    if zdh:
        bekannte_quellen.add("zdh")
    json.dump(sorted(bekannte_quellen), open(quellen_pfad, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    if ohne_redaktion:
        print("HINWEIS - diese Meldungen sind noch nicht redigiert und erscheinen")
        print("          mit dem Originaltitel der Kammer:")
        for k, t in ohne_redaktion:
            print("   ", k, t)

    # Themen in der Reihenfolge ihrer Haeufigkeit. "Ehrungen & Termine" steht
    # immer hinten - das ist der nachrangige Bereich (siehe KMS [D-0173]).
    haeufigkeit = {}
    for x in fertig:
        for t in (x["thema"], x.get("thema2")):
            if t:
                haeufigkeit[t] = haeufigkeit.get(t, 0) + 1
    NACHRANGIG = "Ehrungen & Termine"
    themen = sorted(haeufigkeit,
                    key=lambda t: (t == NACHRANGIG, -haeufigkeit[t], t))
    themen_zahl = haeufigkeit

    # ---- Top-Forderungen mit woertlichem Beleg ----------------------------
    forderungen_datei = json.load(open("daten/forderungen.json", encoding="utf-8"))
    nach_id = {x["id"]: x for x in fertig}
    roh_nach_id = {artikel_id(m["url"]): m for m in meldungen}
    # Belege duerfen auch aus der Bundesebene kommen - Kennung mit "zdh-" davor
    zdh_pfad = "daten/zdh-%s.json" % JAHR
    if os.path.exists(zdh_pfad):
        for x in json.load(open(zdh_pfad, encoding="utf-8")):
            roh_nach_id["zdh-" + x["url"].rstrip("/").split("/")[-1]] = x
    forderungen = []

    for f in forderungen_datei["forderungen"]:
        belege = []
        for b in f["belege"]:
            quelle = roh_nach_id.get(b["id"])
            if not quelle:
                sys.exit("Forderung '%s': Meldung %s gibt es nicht." % (f["kurz"], b["id"]))
            text = " ".join(quelle["volltext"].split())
            start = text.find(b["zitat_ab"])
            if start < 0:
                sys.exit("Forderung '%s': Der Text '%s' steht NICHT in Meldung %s."
                         % (f["kurz"], b["zitat_ab"], b["id"]))
            ausschnitt = text[start:start + ANZEIGE_ZITAT]
            enden = [t.end() for t in SATZ_ENDE.finditer(ausschnitt)]
            if enden:
                ausschnitt = ausschnitt[:enden[-1]]
            # Der Absender kommt bei Bundes-Belegen NICHT aus der
            # Kammer-Erkennung - die ist auf hwk-potsdam.de zugeschnitten
            # und wuerde den ZDH faelschlich als Kammer Potsdam ausweisen.
            if b["id"].startswith("zdh-"):
                wer, ebene = "Zentralverband des Deutschen Handwerks", "Bund"
            else:
                wer, ebene = absender_bestimmen(quelle), "Brandenburg"
            belege.append({
                "id": b["id"],
                "zitat": ausschnitt,
                "datum": nach_id[b["id"]]["datum"],
                "url": quelle["url"],
                "absender": wer,
                "ebene": ebene,
            })
        belege.sort(key=lambda x: x["datum"], reverse=True)
        forderungen.append({
            "kurz": f["kurz"],
            "adressat": f["adressat"],
            "worum": f["worum"],
            "belege": belege,
            "zuletzt": belege[0]["datum"],
            "anzahl": len(belege),
            "ebenen": sorted(set(b["ebene"] for b in belege)),
        })

    daten = {
        "jahr": JAHR,
        "forderungen": forderungen,
        "forderungen_kriterium": forderungen_datei.get("kriterium", ""),
        "stand": redaktion_datei.get("stand", datetime.date.today().isoformat()),
        "themen": themen,
        "letzter_abgleich": heute,
        "neu_anzahl": sum(1 for x in fertig if x["neu"]),
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
