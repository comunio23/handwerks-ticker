# -*- coding: utf-8 -*-
"""
Veroeffentlicht den Handwerks-Ticker auf Netlify.

Hochgeladen wird nicht mehr nur die Seite, sondern alles, was sie zur App
macht:

    ticker-prototyp.html  ->  /index.html
    web/manifest.json     ->  /manifest.json      (Name, Farben, Symbole)
    web/sw.js             ->  /sw.js              (offline + installierbar)
    web/icons/*.png       ->  /icons/*.png

Verwendet die SHA1-Manifest-API, NICHT den ZIP-Upload: Der ZIP-Weg liefert
teils Content-Type text/plain, der Browser zeigt dann Quelltext statt Seite
(KMS [L-0043]).

Der Token kommt aus der Windows-Umgebungsvariablen NETLIFY_AUTH_TOKEN und
steht nirgends im Code.

Aufruf:
    python deploy-netlify.py            (nutzt/erstellt die Site aus netlify-site.json)
    python deploy-netlify.py --vorschau (legt dieselben Dateien nur oertlich
                                         in den Ordner vorschau/, kein Upload)
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


def sammeln():
    """Alle auszuliefernden Dateien als {Netlify-Pfad: lokaler Pfad}."""
    dateien = {"/index.html": QUELLE}
    for name in ("manifest.json", "sw.js"):
        dateien["/" + name] = os.path.join("web", name)
    verzeichnis = os.path.join("web", "icons")
    for name in sorted(os.listdir(verzeichnis)):
        if name.lower().endswith(".png"):
            dateien["/icons/" + name] = os.path.join(verzeichnis, name)

    fehlt = [p for p in dateien.values() if not os.path.exists(p)]
    if fehlt:
        sys.exit("Diese Dateien fehlen: %s%s"
                 % (", ".join(fehlt),
                    "\n(erst 'python baue-ticker.py' laufen lassen)"
                    if QUELLE in fehlt else ""))
    return dateien


def vorschau(dateien):
    """Dieselben Dateien unter denselben Pfaden in den Ordner vorschau/ legen.

    Damit laesst sich die App genau so pruefen, wie sie spaeter ausgeliefert
    wird (Startseite als index.html, Symbole unter /icons/) - ohne sie dafuer
    veroeffentlichen zu muessen.
    """
    import shutil
    ziel = "vorschau"
    if os.path.isdir(ziel):
        shutil.rmtree(ziel)
    for weg, pfad in dateien.items():
        hin = os.path.join(ziel, weg.lstrip("/").replace("/", os.sep))
        os.makedirs(os.path.dirname(hin), exist_ok=True)
        shutil.copyfile(pfad, hin)
        print("  %s" % hin)
    print()
    print("Vorschau bereit. Ansehen mit:")
    print("  python -m http.server 8765 --directory vorschau")


def main():
    hier = os.path.dirname(os.path.abspath(__file__))
    os.chdir(hier)

    dateien = sammeln()
    if "--vorschau" in sys.argv:
        return vorschau(dateien)
    inhalte = {weg: open(pfad, "rb").read() for weg, pfad in dateien.items()}
    pruefsummen = {weg: hashlib.sha1(roh).hexdigest() for weg, roh in inhalte.items()}

    for weg in sorted(dateien):
        print("  %-28s %7.1f kB  %s"
              % (weg, len(inhalte[weg]) / 1024, pruefsummen[weg][:12]))

    site = site_holen()

    # Schritt 1: Netlify das ganze Dateiverzeichnis ankuendigen. Was dort NICHT
    # steht, verschwindet von der Site - deshalb immer alles aufzaehlen.
    deploy = anfrage("/sites/%s/deploys" % site["id"], "POST",
                     {"files": pruefsummen})
    noetig = set(deploy.get("required", []))
    print("Deploy angelegt:", deploy["id"], "| hochzuladen:", len(noetig))

    # Schritt 2: nur die Dateien schicken, die Netlify noch nicht kennt
    for weg in sorted(dateien):
        if pruefsummen[weg] not in noetig:
            print("  unveraendert:", weg)
            continue
        anfrage("%s/deploys/%s/files%s" % (API, deploy["id"], weg),
                "PUT", inhalte[weg], "application/octet-stream")
        print("  uebertragen :", weg)

    stand = anfrage("/deploys/%s" % deploy["id"])
    print()
    print("Zustand :", stand.get("state"))
    print("Adresse :", site.get("ssl_url") or site.get("url"))
    print("Vorschau:", stand.get("deploy_ssl_url") or stand.get("deploy_url"))


if __name__ == "__main__":
    main()
