@echo off
rem ==========================================================================
rem  Handwerks-Ticker - Automatik einschalten (zum Doppelklicken)
rem
rem  Startet automatik-einschalten.ps1. Das legt die Windows-Aufgabe
rem  "Handwerks-Ticker" an: mittwochs und freitags um 7:30 Uhr alle Quellen
rem  holen, Ticker bauen, veroeffentlichen.
rem
rem  Wieder abschalten: automatik-ausschalten.cmd doppelklicken.
rem ==========================================================================
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "automatik-einschalten.ps1"

echo.
echo ----------------------------------------------------------------
echo  Fertig. Dieses Fenster kann geschlossen werden.
echo ----------------------------------------------------------------
pause
