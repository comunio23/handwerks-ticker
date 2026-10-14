# -*- coding: utf-8 -*-
"""
Der eine Abgleich fuer alle Quellen.

Holt der Reihe nach:
  1. Handwerkskammer Potsdam   (scrape-pressemitteilungen.py ueber pruefe-neues.py)
  2. Zentralverband des Deutschen Handwerks (scrape-zdh.py)
  3. Handwerkskammer Frankfurt (Oder) (scrape-hwk-ff.py)
  4. Handwerkskammer Cottbus          (scrape-hwk-cottbus.py)
  5. Junioren des Handwerks e.V.      (scrape-handwerksjunioren.py)
  6. Wirtschaftsministerium Brandenburg (scrape-mweke.py) - die Gegenseite
und baut anschliessend den Ticker neu.

Welche ZDH-Bereiche eingesammelt werden, steht in daten/quellen.json und
laesst sich dort ohne Eingriff in den Code aendern.

Aufruf:
    python abgleich.py                nur holen und bauen
    python abgleich.py --hochladen    zusaetzlich auf Netlify veroeffentlichen

Rueckgabewert: 0 = nichts Neues, 1 = es gibt Neues, 2 = Fehler.
"""
import json
import os
import io
import subprocess
import sys
import datetime

# Die Windows-Konsole kann nicht alle Zeichen darstellen. Ohne diese Umstellung
# bricht der Lauf ab, sobald irgendwo ein Sonderzeichen auftaucht.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HIER = os.path.dirname(os.path.abspath(__file__))
PROTOKOLL = os.path.join("daten", "abgleich-protokoll.txt")


def melde(text=""):
    print(text)
    with open(PROTOKOLL, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def bestand(pfad, schluessel="url"):
    """Welche Eintraege kennen wir aktuell? Fuer den Vorher-Nachher-Vergleich."""
    if not os.path.exists(pfad):
        return set()
    try:
        return {x[schluessel] for x in json.load(open(pfad, encoding="utf-8"))}
    except Exception:
        return set()


def lauf(script, *argumente):
    """Ein Teilscript ausfuehren und seine Ausgabe durchreichen."""
    ergebnis = subprocess.run([sys.executable, script] + list(argumente),
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    for zeile in (ergebnis.stdout or "").splitlines():
        melde("   " + zeile)
    if ergebnis.returncode not in (0, 1):
        melde("   FEHLER in %s (Rueckgabewert %d)" % (script, ergebnis.returncode))
        for zeile in (ergebnis.stderr or "").splitlines()[:10]:
            melde("   ! " + zeile)
    return ergebnis.returncode


def main():
    os.chdir(HIER)
    jahr = str(datetime.date.today().year)
    beginn = datetime.datetime.now()

    melde()
    melde("=" * 66)
    melde("Abgleich am %s" % beginn.strftime("%d.%m.%Y um %H:%M"))
    melde("=" * 66)

    vorher_hwk = bestand("daten/meldungen-%s.json" % jahr)
    vorher_zdh = bestand("daten/zdh-%s.json" % jahr)
    vorher_hwj = bestand("daten/handwerksjunioren-%s.json" % jahr, "kennung")
    vorher_ff = bestand("daten/hwk-ff-%s.json" % jahr, "kennung")
    vorher_cb = bestand("daten/hwk-cottbus-%s.json" % jahr, "kennung")
    vorher_mw = bestand("daten/mweke-%s.json" % jahr, "kennung")

    melde()
    melde("1. Handwerkskammer Potsdam")
    # --nur-holen: pruefe-neues.py soll den Ticker NICHT selbst bauen -
    # das macht Schritt 3, sonst wird zweimal gebaut.
    fehler = lauf("pruefe-neues.py", "--nur-holen") == 2

    melde()
    melde("2. Zentralverband des Deutschen Handwerks")
    if lauf("scrape-zdh.py", jahr) == 2:
        fehler = True

    melde()
    melde("3. Handwerkskammer Frankfurt (Oder)")
    if lauf("scrape-hwk-ff.py", jahr) == 2:
        fehler = True

    melde()
    melde("4. Handwerkskammer Cottbus")
    if lauf("scrape-hwk-cottbus.py", jahr) == 2:
        fehler = True

    melde()
    melde("5. Junioren des Handwerks (Bundesverband)")
    if lauf("scrape-handwerksjunioren.py", jahr) == 2:
        fehler = True

    melde()
    melde("6. Wirtschaftsministerium Brandenburg (Gegenseite)")
    if lauf("scrape-mweke.py", jahr) == 2:
        fehler = True

    nachher_hwk = bestand("daten/meldungen-%s.json" % jahr)
    nachher_zdh = bestand("daten/zdh-%s.json" % jahr)
    nachher_hwj = bestand("daten/handwerksjunioren-%s.json" % jahr, "kennung")
    neu_hwk = nachher_hwk - vorher_hwk
    neu_zdh = nachher_zdh - vorher_zdh
    neu_hwj = nachher_hwj - vorher_hwj
    neu_ff = bestand("daten/hwk-ff-%s.json" % jahr, "kennung") - vorher_ff
    neu_cb = bestand("daten/hwk-cottbus-%s.json" % jahr, "kennung") - vorher_cb
    neu_mw = bestand("daten/mweke-%s.json" % jahr, "kennung") - vorher_mw

    # Den Tag des Abgleichs festhalten, BEVOR gebaut wird. Bisher leitete die
    # Seite ihr Datum aus dem juengsten Fund ab - ein Abgleich, bei dem nichts
    # Neues dabei war, sah damit aus wie gar kein Abgleich.
    stand = {"zuletzt": datetime.date.today().isoformat(),
             "zuletzt_uhrzeit": beginn.strftime("%H:%M"),
             "mit_fehler": bool(fehler)}
    with open("daten/abgleich-stand.json", "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)

    melde()
    melde("7. Ticker bauen")
    if lauf("baue-ticker.py") == 2:
        fehler = True

    melde()
    melde("-" * 66)
    alles_neu = neu_hwk | neu_zdh | neu_hwj | neu_ff | neu_cb | neu_mw
    if alles_neu:
        melde("NEU: %d Potsdam, %d Frankfurt (Oder), %d Cottbus, %d ZDH, "
              "%d Junioren, %d Ministerium"
              % (len(neu_hwk), len(neu_ff), len(neu_cb), len(neu_zdh),
                 len(neu_hwj), len(neu_mw)))
        for u in sorted(alles_neu):
            melde("   " + u)
        melde()
        melde("Diese Meldungen haben noch keinen Redaktionseintrag und erscheinen")
        melde("bis dahin mit ihrem Originaltitel und der Markierung")
        melde("'Noch nicht eingeordnet'.")
    else:
        melde("Nichts Neues.")

    if "--hochladen" in sys.argv and not fehler:
        melde()
        melde("8. Veroeffentlichen")
        if lauf("deploy-netlify.py") == 2:
            fehler = True

    melde("Dauer: %d Sekunden" % (datetime.datetime.now() - beginn).seconds)

    if fehler:
        return 2
    return 1 if (neu_hwk or neu_zdh) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as f:
        melde("FEHLER beim Abgleich: %s" % f)
        sys.exit(2)
