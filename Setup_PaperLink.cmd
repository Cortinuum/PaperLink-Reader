@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup_PaperLink.ps1"
if errorlevel 1 pause
