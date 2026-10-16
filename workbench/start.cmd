@echo off
cd /d "%~dp0\.."
if not exist .venv-workbench\Scripts\python.exe py -3 -m venv .venv-workbench
.venv-workbench\Scripts\python.exe -m pip install -r workbench\requirements.txt
if errorlevel 1 exit /b 1
.venv-workbench\Scripts\python.exe -m playwright install chromium
if errorlevel 1 exit /b 1
.venv-workbench\Scripts\python.exe workbench\server.py %*
