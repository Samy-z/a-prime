@echo off
REM Thin entry for night-pairwise.ps1 (the logic lives there).
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0night-pairwise.ps1"
exit /b %ERRORLEVEL%
