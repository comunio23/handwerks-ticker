@echo off
rem  Taeglicher Abgleich des Handwerks-Tickers.
rem  Holt die Uebersichtsseite der Handwerkskammer, laedt neue Meldungen nach
rem  und baut ticker-prototyp.html neu. Neue Meldungen stehen dort oben.
rem
rem  Von Hand starten: einfach doppelklicken.
rem
rem  Einmal taeglich automatisch (einmalig in der Eingabeaufforderung ausfuehren,
rem  laeuft dann jeden Tag um 7:30 Uhr):
rem
rem     schtasks /create /tn "Handwerks-Ticker" /tr "\"%~f0\"" /sc daily /st 07:30
rem
rem  Wieder entfernen:
rem
rem     schtasks /delete /tn "Handwerks-Ticker" /f

cd /d "%~dp0"
echo ================================================
echo  Handwerks-Ticker - taeglicher Abgleich
echo ================================================
rem  Einmal laufen lassen, Ausgabe in eine Datei - danach auf den Bildschirm.
python pruefe-neues.py > "daten\letzter-abgleich.txt" 2>&1
set ERGEBNIS=%ERRORLEVEL%

type "daten\letzter-abgleich.txt"
type "daten\letzter-abgleich.txt" >> "daten\abgleich-protokoll.txt"

if "%ERGEBNIS%"=="1" (
  echo.
  echo  Es gibt NEUE Meldungen. ticker-prototyp.html wurde aktualisiert.
)
if "%ERGEBNIS%"=="2" (
  echo.
  echo  Beim Abgleich ist ein Fehler aufgetreten.
  echo  Einzelheiten in daten\abgleich-protokoll.txt
)

rem  Fenster offen lassen, wenn von Hand gestartet
if "%1"=="" pause
