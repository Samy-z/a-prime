@echo off
setlocal
REM Launch the cell factorial unattended.
REM
REM Exists because opening Ollama does not start a recording. On 2026-10-04 the
REM server came up on time and sat idle for six hours, because nothing was
REM wired to launch the run. This is that wiring.
REM
REM Usage:  overnight.cmd [hours]      default: no cap, run to completion
REM
REM Called by the Windows scheduled task "aprime-factorial". Safe to run by
REM hand. Two things it does that matter:
REM
REM   1. Clears the stop flag first. A previous --stop leaves a flag on disk and
REM      the next run would exit immediately, which is correct behaviour and a
REM      silly way to lose a night.
REM   2. Appends to logs\overnight.log rather than overwriting, so a morning
REM      check can see every attempt including the ones that failed.
REM
REM If Ollama is not running, the preflight exits in about one second and
REM nothing is wasted. A failed night costs nothing but the log line.
REM
REM Needs the owner logged in: Ollama runs in the user session, so a task under
REM SYSTEM would start a recording against a server that is not there.

cd /d "%~dp0.."

REM No default time cap. Owner instruction, 2026-10-05, after I added caps
REM twice unasked: runs are scoped by choosing which cells to record, so the
REM natural end is "those cells are done". Whether a slowed run keeps going is
REM the owner's call, made with --stop, not a timer's. Pass hours explicitly
REM only when the owner asks for a cap.
set "HOURS=%~1"
if "%HOURS%"=="" set "HOURS=0"

if not exist "logs" mkdir "logs"
set "LOG=logs\overnight.log"

REM Console encoding bites on Windows whenever a model emits a non-ASCII
REM character. Learned the hard way, twice.
set "PYTHONIOENCODING=utf-8"

echo. >> "%LOG%"
echo ================================================================ >> "%LOG%"
echo START %DATE% %TIME%  cap %HOURS%h >> "%LOG%"
echo ================================================================ >> "%LOG%"

".venv\Scripts\python.exe" "scripts\run_study.py" --clear-stop >> "%LOG%" 2>&1

".venv\Scripts\python.exe" -u "scripts\run_study.py" --go --yes --stop-after-hours %HOURS% >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"

echo ---------------------------------------------------------------- >> "%LOG%"
echo END %DATE% %TIME%  exit %RC% >> "%LOG%"

REM Exit codes from run_study.py, for reading the log at a glance:
REM   0 = finished the work it was given
REM   1 = refused to start, or crashed with a traceback
REM   2 = paused, either by the stop flag or by the hour cap. The normal case.
REM   3 = preflight failed, the model server was unreachable
REM   4 = refused to write the matrix because a row was untraceable
REM   6 = the model server died mid-recording
REM
REM Anything except 0 and 2 is a break, and a break at 5am is invisible in a
REM log nobody has opened. Owner request 2026-10-05: put it on screen, so they
REM can see it and ping the agent session to set things back up.
if not "%RC%"=="0" if not "%RC%"=="2" (
  start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0notify.ps1" -Title "a-prime run broke (exit %RC%)" -Message "0/2=ok 1=refused-or-crash 3=server unreachable 4=untraceable rows 6=server died mid-run. See logs\overnight.log, then ping Claude."
)
exit /b %RC%
