@echo off
REM Quick startup script - runs PowerShell startup script
REM Usage: START_PROJECT.bat [model] [--skip-ollama] [--no-browser]

setlocal enabledelayedexpansion
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "START_PROJECT.ps1" %*
