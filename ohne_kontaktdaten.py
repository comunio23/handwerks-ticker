# -*- coding: utf-8 -*-
"""
Entfernt Kontaktdaten aus den eingesammelten Texten, bevor sie gespeichert
werden.

WARUM das sein muss: Am Ende fast jeder Pressemitteilung steht ein
Kontaktblock - Name, Durchwahl und E-Mail der Pressestelle. Auf der
Presseseite der Kammer ist das richtig und gewollt. In unseren Datendateien
ist es etwas anderes: Die liegen in einem OEFFENTLICHEN Repository, sind
maschinenlesbar und lassen sich im Dutzend auslesen. Genau daraus bauen
Adresshaendler ihre Listen.

Gebraucht werden diese Daten hier nie: Der Ticker zeigt Schlagzeile,
Kurzfassung und einen Verweis auf das Original. Wer die Pressestelle
erreichen will, findet sie dort - eine Verlinkung genuegt.

Deshalb: Datensparsamkeit (Art. 5 Abs. 1 lit. c DSGVO). Entfernt werden nur
E-Mail-Adressen, Telefon-, Mobil- und Faxnummern. NAMEN bleiben stehen - sie
sind der Inhalt der Meldung ("Robert Wuest fordert ..."), nicht ihr Anhang.

An die Stelle tritt eine sichtbare Marke statt einer stillen Luecke: Wer den
Text spaeter liest, soll erkennen, dass hier etwas entfernt wurde und es sich
nicht um einen Abruffehler handelt.
"""
import re

MARKE_MAIL = "[E-Mail entfernt]"
MARKE_TELEFON = "[Telefon entfernt]"

# Eine E-Mail-Adresse. Bewusst eng gefasst, damit "Betriebe@Zukunft" o.ae.
# nicht faelschlich getroffen wird.
MAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b")

# Telefon-, Mobil- und Faxnummern, immer mit vorangestelltem Wort - so
# werden Jahreszahlen, Geldbetraege und Hausnummern nicht mitgerissen.
TELEFON = re.compile(
    r"(?i)\b(Tel\.?|Telefon|Telefonnummer|Mobil|Mobiltelefon|Fax|Telefax|Fon)"
    r"\s*[:.]?\s*\+?[\d][\d\s/()\-]{5,}\d")


def entfernen(text):
    """Kontaktdaten aus einem Text nehmen. Gibt (Text, Anzahl) zurueck."""
    if not text:
        return text, 0
    text, mails = MAIL.subn(MARKE_MAIL, text)
    text, telefone = TELEFON.subn(MARKE_TELEFON, text)
    return text, mails + telefone


def saeubern(meldungen, felder=("volltext", "titel", "dachzeile", "anriss")):
    """Eine Liste von Meldungen saeubern. Gibt die Zahl der Funde zurueck."""
    gesamt = 0
    for m in meldungen:
        if not isinstance(m, dict):
            continue
        for feld in felder:
            if isinstance(m.get(feld), str):
                m[feld], anzahl = entfernen(m[feld])
                gesamt += anzahl
    return gesamt


def melden(anzahl):
    """Einheitlicher Hinweis fuer die Abruf-Protokolle."""
    if anzahl:
        print("   Kontaktdaten entfernt (Datensparsamkeit): %d" % anzahl)
