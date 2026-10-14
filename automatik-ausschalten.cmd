@echo off
rem ==========================================================================
rem  Handwerks-Ticker - Automatik ausschalten (zum Doppelklicken)
rem
rem  Entfernt die Windows-Aufgabe "Handwerks-Ticker" wieder. Der Ticker
rem  bleibt, wie er ist, und laesst sich weiter von Hand aktualisieren:
rem  abgleich-automatisch.cmd doppelklicken.
rem ==========================================================================
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "automatik-einschalten.ps1" -Aus

echo.
pause
