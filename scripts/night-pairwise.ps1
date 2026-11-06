# One night, two stages, no cap (the owner stops runs, timers do not):
#   1. Record the assistante-ventes pairwise store to completion
#      (compare/pairwise_ventes.py --go; four-arm tuples, CPU only,
#      resumes wherever the store stands, ~19 s per remaining tuple).
#   2. Score it (--analyse; loads the NLI judge on the GPU, refuses if a
#      main-line recorder is running or the store is partial).
# Starts Ollama itself if the server is down. Toasts on skip, pause,
# break and completion. Log: logs\pairwise.log.

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path "logs")) { New-Item -ItemType Directory "logs" | Out-Null }
$log = Join-Path $root "logs\pairwise.log"
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

Write-Log "================ pairwise night start ================"

$recorders = @(Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'run_study|run_cell_detection|run_drift_control|pairwise_ventes' })
if ($recorders.Count -gt 0) {
    Write-Log "SKIPPED: a recorder is already running, leaving it alone"
    Send-Toast "pairwise night skipped" "Another recording is already running; nothing was started twice."
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
        Send-Toast "pairwise night: Ollama would not start" "Nothing recorded. See logs\pairwise.log, then ping Claude."
        exit 3
    }
    Write-Log "server is up"
}

$py = Join-Path $root ".venv\Scripts\python.exe"
cmd /c "`"$py`" compare\pairwise_ventes.py --clear-stop >> `"$log`" 2>&1" | Out-Null

$stages = @(
    @{ name = "record (four-arm tuples, CPU)"
       cmd  = "`"$py`" -u compare\pairwise_ventes.py --go" },
    @{ name = "analyse (NLI judge, GPU)"
       cmd  = "`"$py`" -u compare\pairwise_ventes.py --analyse" }
)
foreach ($stage in $stages) {
    Write-Log "---- stage '$($stage.name)'"
    cmd /c "$($stage.cmd) >> `"$log`" 2>&1"
    $rc = $LASTEXITCODE
    Write-Log "---- stage '$($stage.name)' exit $rc"
    if ($rc -eq 2) {
        Write-Log "paused; ending the night"
        Send-Toast "pairwise night paused" "A stop ended the night cleanly. The store resumes; see logs\pairwise.log."
        exit 2
    }
    if ($rc -ne 0) {
        Send-Toast "pairwise night broke (exit $rc)" "Stage: $($stage.name). 3=recorder or server in the way 4=preflight empty 5=digest changed 6=repeated failures 7=tuples missing. See logs\pairwise.log, then ping Claude."
        exit $rc
    }
}

Write-Log "================ pairwise night complete ================"
Send-Toast "pairwise night complete" "Store recorded and scored. The report is compare\results\pairwise-ventes.report.txt. The flags are the human judging queue."
exit 0
