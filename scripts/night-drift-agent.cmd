@echo off
REM Thin entry for night-drift-agent.ps1 (the logic lives there).
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0night-drift-agent.ps1"
exit /b %ERRORLEVEL%
