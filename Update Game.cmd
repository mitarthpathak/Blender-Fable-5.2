@echo off
rem Double-click: pull the latest work and rebuild the game's .exe files and shortcuts.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\update_and_build.ps1" %*
pause
