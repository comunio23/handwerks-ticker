# ===========================================================================
#  Handwerks-Ticker - Automatik ein- oder ausschalten
#
#  Legt die Windows-Aufgabe "Handwerks-Ticker" an. Sie startet mittwochs und
#  freitags um 7:30 Uhr abgleich-automatisch.cmd: alle fuenf Quellen holen,
#  Ticker bauen, auf Netlify veroeffentlichen.
#
#  Warum Mittwoch UND Freitag? Gemessen am Jahrgang 2026 (412 Meldungen):
#  dienstags erscheint am meisten (136), am Wochenende fast nichts. Mit
#  diesen beiden Tagen liegt eine Meldung im Schnitt 2,0 Tage unbemerkt
#  herum, mit nur einem Tag 3,7 Tage.
#
#  Einschalten:
#      powershell -ExecutionPolicy Bypass -File automatik-einschalten.ps1
#  Ausschalten:
#      powershell -ExecutionPolicy Bypass -File automatik-einschalten.ps1 -Aus
#
#  Es werden keine Administratorrechte gebraucht. Die Aufgabe laeuft unter
#  dem angemeldeten Benutzer - sie braucht den Netlify-Token aus der
#  Umgebungsvariablen und die Git-Anmeldung, beides gibt es nur dort.
# ===========================================================================
param([switch]$Aus)

$name = "Handwerks-Ticker"
$ordner = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Aus) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "Automatik abgeschaltet. Der Ticker laesst sich weiter von Hand"
    Write-Host "aktualisieren: abgleich-automatisch.cmd doppelklicken."
    return
}

# Fenster versteckt: Der Abgleich dauert einige Minuten, in denen sonst
# zweimal pro Woche eine schwarze Konsole mitten in der Arbeit stuende.
$aktion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"& '.\abgleich-automatisch.cmd' still`"" `
    -WorkingDirectory $ordner

$ausloeser = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday,Friday -At 7:30am

# StartWhenAvailable: War der Rechner um 7:30 aus, laeuft der Abgleich beim
# naechsten Start nach. RestartCount: bei Netzproblemen drei Versuche im
# Stundenabstand.
$einstellungen = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $name -Action $aktion -Trigger $ausloeser `
    -Settings $einstellungen -Force `
    -Description "Gleicht die Quellen des Handwerks-Tickers ab und veroeffentlicht ihn. Mittwochs und freitags 7:30 Uhr." | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $name
Write-Host ""
Write-Host "Automatik eingeschaltet."
Write-Host ("  Naechster Lauf : " + $info.NextRunTime)
Write-Host "  Takt           : mittwochs und freitags, 7:30 Uhr"
Write-Host ""
Write-Host "Sofort einmal laufen lassen (dauert einige Minuten):"
Write-Host "  Start-ScheduledTask -TaskName '$name'"
Write-Host ""
Write-Host "Nachsehen, wie es lief:"
Write-Host "  Get-ScheduledTaskInfo -TaskName '$name'"
Write-Host "  Get-Content 'daten\letzter-abgleich.txt' -Tail 30"
