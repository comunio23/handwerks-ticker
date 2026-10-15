# ===========================================================================
#  Handwerks-Ticker - Kontaktdaten aus der Git-Historie entfernen
#
#  Was dieses Skript tut, der Reihe nach:
#    1. Sicherung der kompletten Historie als .bundle auf den Desktop
#    2. Den bereits vorbereiteten Commit normal pushen
#    3. RUECKFRAGE
#    4. Alle Commits umschreiben: E-Mail-Adressen, Telefon-, Mobil- und
#       Faxnummern aus daten/*.json ersetzen
#    5. Alte Sicherungszeiger von Git loeschen und aufraeumen
#    6. PRUEFEN - findet sich noch eine Adresse, bricht es hier ab und
#       pusht NICHT
#    7. Erzwungener Push
#    8. Gegenprobe gegen GitHub: frischer Klon, erneute Suche
#
#  WICHTIG, bevor du startest:
#    * Alle Commits bekommen neue Kennungen. Alte Verweise (auch die im
#      KMS-Logbuch) zeigen danach ins Leere. Der Inhalt bleibt derselbe.
#    * Das ist ein erzwungener Push auf ein oeffentliches Repository. Bei
#      einem Projekt ohne Mitarbeiter ist das unkritisch - es gibt niemanden,
#      dessen Arbeitsstand dadurch kaputtgeht.
#    * Rueckweg: git clone <Pfad zur .bundle-Datei>
#
#  Aufruf: historie-saeubern.cmd doppelklicken
# ===========================================================================
$ErrorActionPreference = "Stop"
$ordner = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ordner

function Titel($text) {
    Write-Host ""
    Write-Host ("=" * 70)
    Write-Host "  $text"
    Write-Host ("=" * 70)
}

# --------------------------------------------------------------- 1. Sicherung
Titel "1. Sicherung"
$stempel = Get-Date -Format "yyyy-MM-dd-HHmm"
$sicherung = Join-Path ([Environment]::GetFolderPath("Desktop")) "handwerks-ticker-sicherung-$stempel.bundle"
git bundle create "$sicherung" --all
if ($LASTEXITCODE -ne 0) { Write-Host "Sicherung fehlgeschlagen - Abbruch."; pause; exit 1 }
Write-Host "Gesichert: $sicherung"
Write-Host "Zurueckholen im Notfall:  git clone `"$sicherung`" wiederhergestellt"

# ------------------------------------------------------- 2. Normaler Push
Titel "2. Den gesaeuberten Stand pushen"
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Host "Push fehlgeschlagen - Abbruch."; pause; exit 1 }

# ------------------------------------------------------------ 3. Rueckfrage
Titel "3. Jetzt wird die Historie umgeschrieben"
Write-Host "Alle Commits bekommen neue Kennungen. Das ist nicht rueckholbar"
Write-Host "(ausser ueber die Sicherung von eben)."
Write-Host ""
$antwort = Read-Host "Weitermachen? Tippe JA und Enter"
if ($antwort -ne "JA") { Write-Host "Abgebrochen. Es wurde nichts umgeschrieben."; pause; exit 0 }

# ------------------------------------------------------ 4. Historie umschreiben
Titel "4. Historie umschreiben"
$env:FILTER_BRANCH_SQUELCH_WARNING = "1"
$filter = Join-Path $ordner "historie-saeubern.py"
git filter-branch --force --tree-filter "python -I `"$filter`"" -- --all
if ($LASTEXITCODE -ne 0) { Write-Host "Umschreiben fehlgeschlagen - NICHT gepusht."; pause; exit 1 }

# ----------------------------------------------------------- 5. Aufraeumen
Titel "5. Aufraeumen"
git for-each-ref --format="%(refname)" refs/original/ | ForEach-Object {
    if ($_) { git update-ref -d $_ }
}
git reflog expire --expire=now --all
git gc --prune=now
Write-Host "Alte Sicherungszeiger entfernt."

# -------------------------------------------------------------- 6. Pruefen
Titel "6. Pruefen - ist wirklich nichts mehr da?"
$pruefung = python -I -c @"
import re, subprocess, sys
MAIL = re.compile(rb'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b')
objekte = [z.split(' ', 1) for z in subprocess.run(['git','rev-list','--objects','--all'],
           capture_output=True, text=True, encoding='utf-8').stdout.splitlines() if ' ' in z]
gefunden = set()
for sha, name in objekte:
    if not name.endswith('.json'): continue
    roh = subprocess.run(['git','cat-file','-p',sha], capture_output=True).stdout
    gefunden |= {a for a in MAIL.findall(roh) if b'entfernt' not in a}
print(len(gefunden))
for a in sorted(gefunden)[:10]: print('   REST:', a.decode())
"@
$zeilen = $pruefung -split "`n"
$anzahl = [int]($zeilen[0].Trim())
Write-Host $pruefung
if ($anzahl -ne 0) {
    Write-Host ""
    Write-Host "Es sind noch $anzahl Adressen in der Historie. Es wird NICHT gepusht."
    Write-Host "Der lokale Stand ist umgeschrieben, GitHub unveraendert."
    pause; exit 1
}
Write-Host "Keine Adressen mehr in der Historie."

# ---------------------------------------------------------- 7. Erzwungener Push
Titel "7. Erzwungener Push"
git push --force-with-lease origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Push fehlgeschlagen. Lokal ist alles gesaeubert, GitHub noch nicht."
    pause; exit 1
}

# ------------------------------------------------------------- 8. Gegenprobe
Titel "8. Gegenprobe gegen GitHub"
$temp = Join-Path $env:TEMP "ticker-gegenprobe-$stempel"
git clone --quiet https://github.com/comunio23/handwerks-ticker.git "$temp"
if ($LASTEXITCODE -eq 0) {
    Push-Location "$temp"
    $rest = python -I -c @"
import re, subprocess
MAIL = re.compile(rb'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b')
objekte = [z.split(' ', 1) for z in subprocess.run(['git','rev-list','--objects','--all'],
           capture_output=True, text=True, encoding='utf-8').stdout.splitlines() if ' ' in z]
g = set()
for sha, name in objekte:
    if not name.endswith('.json'): continue
    roh = subprocess.run(['git','cat-file','-p',sha], capture_output=True).stdout
    g |= {a for a in MAIL.findall(roh) if b'entfernt' not in a}
print('Adressen im frisch geklonten Repository:', len(g))
"@
    Write-Host $rest
    Pop-Location
    Remove-Item -Recurse -Force "$temp" -ErrorAction SilentlyContinue
}

Titel "Fertig"
Write-Host "Die Sicherung liegt auf dem Desktop:"
Write-Host "  $sicherung"
Write-Host ""
Write-Host "Hinweis: GitHub kann alte Objekte noch eine Weile ueber ihre"
Write-Host "direkte Kennung ausliefern. Wer das endgueltig weg haben will,"
Write-Host "bittet den GitHub-Support um ein 'garbage collection' des Repos."
pause
