# One night, two stages, no cap (the owner stops runs, timers do not):
#   1. The drift negative control (~1 h: record three baseline arms of
#      banking-summary, score against the 2026-10-04 pair; MTH-026).
#   2. The banking-agent cell at k=20 (~11 h), the first data point of the
#      agent self-variance investigation (methods STATE, 2026-10-17).
# Starts Ollama itself if the server is down. Toasts on break, pause and
# completion. Log: logs\drift-agent.log.

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path "logs")) { New-Item -ItemType Directory "logs" | Out-Null }
$log = Join-Path $root "logs\drift-agent.log"
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

Write-Log "================ drift + agent-k20 night start ================"

$recorders = @(Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'run_study|run_cell_detection|run_drift_control' })
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
        Send-Toast "a-prime night: Ollama would not start" "Nothing recorded. See logs\drift-agent.log, then ping Claude."
        exit 3
    }
    Write-Log "server is up"
}

$py = Join-Path $root ".venv\Scripts\python.exe"
cmd /c "`"$py`" scripts\run_study.py --clear-stop >> `"$log`" 2>&1" | Out-Null

$stages = @(
    @{ name = "drift negative control (MTH-026)"
       cmd  = "`"$py`" -u scripts\run_drift_control.py --go" },
    @{ name = "banking-agent at k=20"
       cmd  = "`"$py`" -u scripts\run_study.py --go --yes --only-domain banking --only-format agent --k 20" }
)
foreach ($stage in $stages) {
    Write-Log "---- stage '$($stage.name)'"
    cmd /c "$($stage.cmd) >> `"$log`" 2>&1"
    $rc = $LASTEXITCODE
    Write-Log "---- stage '$($stage.name)' exit $rc"
    if ($rc -eq 2) {
        Write-Log "paused; ending the night"
        Send-Toast "a-prime night paused" "A stop ended the night cleanly mid-plan. See logs\drift-agent.log for where it got to."
        exit 2
    }
    if ($rc -ne 0) {
        Send-Toast "a-prime night broke (exit $rc)" "Stage: $($stage.name). 3=server down 4=corpus mismatch 5=digest changed 6=server died. See logs\drift-agent.log, then ping Claude."
        exit $rc
    }
}

Write-Log "================ night complete ================"
Send-Toast "a-prime night complete" "Drift control scored and the banking-agent k=20 cell is recorded and analysed."
exit 0
