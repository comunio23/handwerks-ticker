@echo off
rem ==========================================================================
rem  Handwerks-Ticker - Abgleich aller Quellen
rem
rem  Holt die Handwerkskammer Potsdam und den Zentralverband des Deutschen
rem  Handwerks, baut den Ticker neu und veroeffentlicht ihn auf Netlify.
rem  Welche ZDH-Bereiche dabei sind, steht in daten\quellen.json.
rem
rem  Von Hand starten: doppelklicken.
rem
rem  ------------------------------------------------------------------------
rem  Automatisch jeden Mittwoch um 7:30 Uhr - EINMALIG in der
rem  Eingabeaufforderung ausfuehren:
rem
rem    schtasks /create /tn "Handwerks-Ticker" /sc weekly /d MI /st 07:30 ^
rem      /tr "\"%~f0\" still"
rem
rem  Taeglich statt woechentlich:
rem
rem    schtasks /create /tn "Handwerks-Ticker" /sc daily /st 07:30 ^
rem      /tr "\"%~f0\" still"
rem
rem  Wieder entfernen:
rem
rem    schtasks /delete /tn "Handwerks-Ticker" /f
rem
rem  Nachsehen, wann er zuletzt lief:
rem
rem    schtasks /query /tn "Handwerks-Ticker" /v /fo LIST
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
