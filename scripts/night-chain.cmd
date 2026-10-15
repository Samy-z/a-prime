@echo off
REM Thin task-scheduler entry for night-chain.ps1 (the logic lives there).
REM Scheduled once for 2026-10-15 23:00 with the owner's 23 h window.
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0night-chain.ps1" -WindowHours 23
exit /b %ERRORLEVEL%
