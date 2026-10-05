@echo off
setlocal
REM One-shot launcher for the D25 test run: the summary row at k=20, no cap.
REM Scheduled once for 2026-10-06 23:00. HANDOFF section 21 holds the decision
REM and the pre-registered prediction this run tests.
REM
REM Steps, each visible in logs\k20.log:
REM   1. Refuse if another recorder is already running (two recorders thrash
REM      the GPU and interleave model loads; different configs never share a
REM      checkpoint file, so this is collision avoidance, not a cap).
REM   2. Remove the daily 05:00 task: by tonight the k=6 factorial is done and
REM      a 05:00 firing would unload the model mid-run for its analysis pass.
REM   3. Pull main, because the --k flag lands from the cloud session.
REM   4. Record the summary row at k=20. New config hash, new checkpoint
REM      files, beside the k=6 ones, by design.
REM Any bad exit fires the on-screen notification.

cd /d "%~dp0.."
if not exist "logs" mkdir "logs"
set "LOG=logs\k20.log"
set "PYTHONIOENCODING=utf-8"

echo. >> "%LOG%"
echo ================ START %DATE% %TIME% k=20 summary row ================ >> "%LOG%"

tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /I "python.exe" >nul
if not errorlevel 1 (
  echo SKIPPED: another python run is active >> "%LOG%"
  start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0notify.ps1" -Title "a-prime k=20 run skipped" -Message "Another run was still active at 23:00. Nothing started. Ping Claude."
  exit /b 7
)

schtasks /Delete /TN "aprime-factorial" /F >> "%LOG%" 2>&1

git pull --ff-only >> "%LOG%" 2>&1

".venv\Scripts\python.exe" -u "scripts\run_study.py" --clear-stop >> "%LOG%" 2>&1
".venv\Scripts\python.exe" -u "scripts\run_study.py" --go --yes --only-format summary --k 20 >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo ---------------- END %DATE% %TIME% exit %RC% ---------------- >> "%LOG%"

if not "%RC%"=="0" if not "%RC%"=="2" (
  start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0notify.ps1" -Title "a-prime k=20 run broke (exit %RC%)" -Message "See logs\k20.log, then ping Claude. 2=paused-by-stop is normal; 3=server down; unknown flag means the --k change has not landed."
)
exit /b %RC%
