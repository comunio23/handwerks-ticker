@echo off
rem ==========================================================================
rem  Handwerks-Ticker - Kontaktdaten aus der Git-Historie entfernen
rem
rem  Doppelklicken. Das Skript sichert zuerst, fragt vor dem unwiderruflichen
rem  Teil nach und pusht nur, wenn die Pruefung sauber ist.
rem  Einzelheiten stehen in historie-saeubern.ps1.
rem ==========================================================================
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "historie-saeubern.ps1"
