# -*- coding: utf-8 -*-
"""
Veroeffentlicht ticker-prototyp.html als index.html auf Netlify.

Verwendet die SHA1-Manifest-API, NICHT den ZIP-Upload: Der ZIP-Weg liefert
teils Content-Type text/plain, der Browser zeigt dann Quelltext statt Seite
(KMS [L-0043]).

Der Token kommt aus der Windows-Umgebungsvariablen NETLIFY_AUTH_TOKEN und
steht nirgends im Code.

Aufruf:
    python deploy-netlify.py            (nutzt/erstellt die Site aus netlify-site.json)
"""
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error

API = "https://api.netlify.com/api/v1"
SITE_MERKER = "netlify-site.json"
WUNSCHNAME = "handwerks-ticker"
QUELLE = "ticker-prototyp.html"


def token():
    t = os.environ.get("NETLIFY_AUTH_TOKEN")
    if not t:
        sys.exit("NETLIFY_AUTH_TOKEN ist nicht gesetzt.")
    return t


def anfrage(weg, methode="GET", koerper=None, typ="application/json"):
    url = weg if weg.startswith("http") else API + weg
    daten = None
    if koerper is not None:
        daten = koerper if isinstance(koerper, bytes) else json.dumps(koerper).encode("utf-8")
    req = urllib.request.Request(url, data=daten, method=methode)
    req.add_header("Authorization", "Bearer " + token())
    if daten is not None:
        req.add_header("Content-Type", typ)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            roh = r.read()
            return json.loads(roh) if roh else {}
    except urllib.error.HTTPError as f:
        sys.exit("Netlify-Fehler %s bei %s %s:\n%s"
                 % (f.code, methode, url, f.read().decode("utf-8", "replace")[:800]))


def site_holen():
    """Bekannte Site wiederverwenden, sonst eine neue anlegen."""
    if os.path.exists(SITE_MERKER):
        gemerkt = json.load(open(SITE_MERKER, encoding="utf-8"))
        vorhanden = anfrage("/sites/" + gemerkt["site_id"])
        print("Bestehende Site:", vorhanden["name"])
        return vorhanden

    for versuch in range(5):
        name = WUNSCHNAME if versuch == 0 else "%s-%d" % (WUNSCHNAME, versuch + 1)
        try:
            neu = anfrage("/sites", "POST", {"name": name})
            print("Neue Site angelegt:", neu["name"])
            json.dump({"site_id": neu["id"], "name": neu["name"]},
                      open(SITE_MERKER, "w", encoding="utf-8"), indent=1)
            return neu
        except SystemExit as fehler:
            if "422" not in str(fehler):
                raise
            print("  Name '%s' ist vergeben, naechster Versuch ..." % name)
    sys.exit("Kein freier Site-Name gefunden.")


def main():
    hier = os.path.dirname(os.path.abspath(__file__))
    os.chdir(hier)

    if not os.path.exists(QUELLE):
        sys.exit("%s fehlt - erst 'python baue-ticker.py' laufen lassen." % QUELLE)

    inhalt = open(QUELLE, "rb").read()
    pruefsumme = hashlib.sha1(inhalt).hexdigest()      # Netlify erwartet SHA1
    print("%s: %.0f kB, SHA1 %s" % (QUELLE, len(inhalt) / 1024, pruefsumme[:12]))

    site = site_holen()

    # Schritt 1: Netlify das Dateiverzeichnis ankuendigen
    deploy = anfrage("/sites/%s/deploys" % site["id"], "POST",
                     {"files": {"/index.html": pruefsumme}})
    fehlend = deploy.get("required", [])
    print("Deploy angelegt:", deploy["id"], "| noch hochzuladen:", len(fehlend))

    # Schritt 2: die Datei selbst schicken
    if pruefsumme in fehlend or fehlend:
        anfrage("%s/deploys/%s/files/index.html" % (API, deploy["id"]),
                "PUT", inhalt, "application/octet-stream")
        print("Datei uebertragen.")

    stand = anfrage("/deploys/%s" % deploy["id"])
    print()
    print("Zustand :", stand.get("state"))
    print("Adresse :", site.get("ssl_url") or site.get("url"))
    print("Vorschau:", stand.get("deploy_ssl_url") or stand.get("deploy_url"))


if __name__ == "__main__":
    main()
