@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo ScanPDF Studio is not installed. Run INSTALL.bat first.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m scanpdf

