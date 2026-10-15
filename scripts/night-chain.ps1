# One night, three stages, one owner-given window (2026-10-15, 23 h):
#   1. Finish the k=6 factorial: the two remaining agent cells, then phase 2
#      writes the nine-cell matrix.
#   2. The k=20 summary row -- the pre-registered D25 test (HANDOFF section 21).
#   3. The k=20 banking-extraction re-record (ratified 2026-10-06, HANDOFF
#      section 21 amendment).
# Each stage gets whatever is left of the window as its --stop-after-hours;
# the window is the owner's instruction for this night, not a standing cap.
#
# Unlike the earlier launchers this one also STARTS Ollama if the server is
# down: the 2026-10-09 05:00 firing died on exit 3 for exactly that, and a
# chain scheduled at 23:00 cannot assume anyone opened the app first.

param([double]$WindowHours = 23)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path "logs")) { New-Item -ItemType Directory "logs" | Out-Null }
$log = Join-Path $root "logs\chain.log"
$env:PYTHONIOENCODING = "utf-8"

function Write-Log($m) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $m" | Add-Content $log
}
function Send-Toast($title, $msg) {
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", "$PSScriptRoot\notify.ps1", "-Title", $title, "-Message", $msg
}
function Test-Server {
    try {
        Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 | Out-Null
        $true
    } catch { $false }
}

Write-Log "================ chain start, window $WindowHours h ================"

# Same guard as the other launchers: a recorder's command line, not python.exe.
$recorders = @(Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'run_study|run_cell_detection' })
if ($recorders.Count -gt 0) {
    Write-Log "SKIPPED: a recorder is already running, leaving it alone"
    exit 0
}

if (-not (Test-Server)) {
    Write-Log "Ollama is down, starting it"
    Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
    $up = $false
    foreach ($i in 1..40) {
        Start-Sleep -Seconds 3
        if (Test-Server) { $up = $true; break }
    }
    if (-not $up) {
        Write-Log "server did not come up within 2 min"
        Send-Toast "a-prime chain: Ollama would not start" "Nothing recorded. See logs\chain.log, then ping Claude."
        exit 3
    }
    Write-Log "server is up"
}

$deadline = (Get-Date).AddHours($WindowHours)
$py = Join-Path $root ".venv\Scripts\python.exe"

cmd /c "`"$py`" scripts\run_study.py --clear-stop >> `"$log`" 2>&1" | Out-Null

$stages = @(
    @{ name = "k=6 factorial: agent row, then the nine-cell matrix"
       args = "--go --yes" },
    @{ name = "k=20 summary row (D25 test)"
       args = "--go --yes --only-format summary --k 20" },
    @{ name = "k=20 banking-extraction re-record"
       args = "--go --yes --only-domain banking --only-format extraction --k 20" }
)

foreach ($stage in $stages) {
    $remaining = ($deadline - (Get-Date)).TotalHours
    if ($remaining -lt 0.25) {
        Write-Log "window exhausted before '$($stage.name)'; stopping here"
        break
    }
    $cap = [math]::Round($remaining, 2)
    Write-Log "---- stage '$($stage.name)', cap $cap h"
    cmd /c "`"$py`" -u scripts\run_study.py $($stage.args) --stop-after-hours $cap >> `"$log`" 2>&1"
    $rc = $LASTEXITCODE
    Write-Log "---- stage '$($stage.name)' exit $rc"
    if ($rc -eq 2) {
        # Paused by the window cap or a --stop: clean, nothing after it runs.
        Write-Log "paused; ending the chain"
        Send-Toast "a-prime chain paused" "The window or a stop ended the night cleanly mid-plan. See logs\chain.log for where it got to."
        exit 2
    }
    if ($rc -ne 0) {
        Send-Toast "a-prime chain broke (exit $rc)" "Stage: $($stage.name). 3=server down 6=server died mid-run. See logs\chain.log, then ping Claude."
        exit $rc
    }
}

Write-Log "================ chain complete ================"
Send-Toast "a-prime chain complete" "All three stages recorded and analysed. The nine-cell matrix and both k=20 rows are on disk."
exit 0
