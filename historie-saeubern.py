# -*- coding: utf-8 -*-
"""Wird von 'git filter-branch --tree-filter' in JEDEM Commit ausgefuehrt.

Entfernt dieselben Kontaktdaten wie ohne_kontaktdaten.py - aber aus den
ausgecheckten Dateien des jeweiligen alten Standes. Bewusst OHNE Import aus
dem Projekt: In alten Commits gibt es ohne_kontaktdaten.py noch gar nicht.

Bricht nie ab. Ein Fehler hier wuerde die Umschreibung der Historie mitten im
Lauf stoppen, und das waere schlimmer als eine nicht gesaeuberte Fassung.
"""
import glob
import os
import re
import sys

MAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b")
TELEFON = re.compile(
    r"(?i)\b(Tel\.?|Telefon|Telefonnummer|Mobil|Mobiltelefon|Fax|Telefax|Fon)"
    r"\s*[:.]?\s*\+?[\d][\d\s/()\-]{5,}\d")

geaendert = 0
try:
    for pfad in glob.glob(os.path.join("daten", "*.json")):
        try:
            roh = open(pfad, encoding="utf-8").read()
        except OSError:
            continue
        neu = TELEFON.sub("[Telefon entfernt]", MAIL.sub("[E-Mail entfernt]", roh))
        if neu != roh:
            open(pfad, "w", encoding="utf-8").write(neu)
            geaendert += 1
except Exception as f:                      # nie den Lauf abbrechen
    print("Hinweis: %s" % f, file=sys.stderr)

sys.exit(0)
