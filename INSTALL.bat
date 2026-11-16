@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo Python environment manager uv not found.
  echo Install uv from https://docs.astral.sh/uv/ and rerun this file.
  pause
  exit /b 1
)
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -e . pytest reportlab pyinstaller
if errorlevel 1 (
  echo Installation failed. See the output above.
  pause
  exit /b 1
)
echo.
echo Installation complete. Run RUN.bat.
pause

