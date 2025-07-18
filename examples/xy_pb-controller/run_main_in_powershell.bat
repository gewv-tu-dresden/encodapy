@echo off
REM Gehe ins Verzeichnis dieser Datei (wo main.py liegt)
cd /d "%~dp0"

REM Setze den PythonPath auf das Projektverzeichnis
set PYTHONPATH=%CD%

REM Starte PowerShell mit Python aus der venv
powershell -NoExit -Command "& '%CD%\..\..\.venv\Scripts\python.exe' main.py"
