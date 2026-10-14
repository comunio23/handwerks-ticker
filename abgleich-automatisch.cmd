@echo off
rem ==========================================================================
rem  Handwerks-Ticker - Abgleich aller Quellen
rem
rem  Holt die Handwerkskammern Potsdam, Frankfurt (Oder) und Cottbus, den
rem  Zentralverband des Deutschen Handwerks und die Junioren des Handwerks,
rem  baut den Ticker neu und veroeffentlicht ihn auf Netlify.
rem  Welche Bereiche dabei sind, steht in daten\quellen.json.
rem
rem  Von Hand starten: doppelklicken.
rem
rem  ------------------------------------------------------------------------
rem  AUTOMATIK
rem
rem  Laeuft als Windows-Aufgabe "Handwerks-Ticker" mittwochs und freitags um
rem  7:30 Uhr. Mittwoch und Freitag deshalb, weil die Quellen dienstags am
rem  meisten veroeffentlichen (136 von 412 Meldungen des Jahrgangs) und das
rem  Wochenende leer ist: Mit diesen beiden Tagen liegt eine Meldung im
rem  Schnitt 2,0 Tage, mit nur einem Tag 3,7 Tage unbemerkt herum.
rem
rem  War der Rechner aus, holt Windows den Lauf beim naechsten Start nach
rem  (StartWhenAvailable). Die Seite selbst warnt sichtbar, wenn der letzte
rem  Abgleich mehr als acht Tage her ist.
rem
rem  Nachsehen, wann sie zuletzt lief:
rem    schtasks /query /tn "Handwerks-Ticker" /v /fo LIST
rem
rem  Sofort einmal laufen lassen:
rem    schtasks /run /tn "Handwerks-Ticker"
rem
rem  Takt aendern (Beispiel: zusaetzlich montags):
rem    schtasks /change /tn "Handwerks-Ticker" /sc weekly /d MO,MI,FR /st 07:30
rem    ... und daten\quellen.json anpassen, sonst nennt die Seite den alten Takt.
rem
rem  Automatik wieder abschalten:
rem    schtasks /delete /tn "Handwerks-Ticker" /f
rem  ==========================================================================

cd /d "%~dp0"

echo ================================================
echo  Handwerks-Ticker - Abgleich aller Quellen
echo  Das dauert einige Minuten (hoeflicher Abruf).
echo ================================================
echo.

python abgleich.py --hochladen > "daten\letzter-abgleich.txt" 2>&1
set ERGEBNIS=%ERRORLEVEL%

type "daten\letzter-abgleich.txt"

echo.
if "%ERGEBNIS%"=="1" (
  echo  Es gibt NEUE Meldungen. Der Ticker wurde aktualisiert.
  echo  Sie stehen dort oben und tragen noch ihren Originaltitel,
  echo  bis sie zusammengefasst sind.
)
if "%ERGEBNIS%"=="0" echo  Nichts Neues gefunden.
if "%ERGEBNIS%"=="2" (
  echo  Beim Abgleich ist ein Fehler aufgetreten.
  echo  Einzelheiten in daten\abgleich-protokoll.txt
)

rem  Fenster offen lassen, wenn von Hand gestartet - beim Zeitplan nicht
if not "%1"=="still" pause
