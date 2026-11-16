@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run INSTALL.bat first.
  pause
  exit /b 1
)

rem Keep PyInstaller and PaddleX caches independent from a restricted user profile.
set "BUILD_HOME=%~dp0.build-home"
set "USERPROFILE=%BUILD_HOME%"
set "HOME=%BUILD_HOME%"
set "APPDATA=%BUILD_HOME%\AppData\Roaming"
set "LOCALAPPDATA=%BUILD_HOME%\AppData\Local"
set "TEMP=%BUILD_HOME%\tmp"
set "TMP=%BUILD_HOME%\tmp"
set "PADDLE_PDX_CACHE_HOME=%BUILD_HOME%\.paddlex"
set "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True"
set "DISABLE_MODEL_SOURCE_CHECK=True"
if not exist "%APPDATA%" mkdir "%APPDATA%"
if not exist "%LOCALAPPDATA%" mkdir "%LOCALAPPDATA%"
if not exist "%TEMP%" mkdir "%TEMP%"
if not exist "%PADDLE_PDX_CACHE_HOME%" mkdir "%PADDLE_PDX_CACHE_HOME%"

".venv\Scripts\python.exe" -m pytest
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean ScanPDFStudio.spec
if errorlevel 1 exit /b 1
copy /Y README.md "dist\ScanPDFStudio\README.md" >nul
if errorlevel 1 exit /b 1
copy /Y TEST_REPORT.md "dist\ScanPDFStudio\TEST_REPORT.md" >nul
if errorlevel 1 exit /b 1
copy /Y THIRD_PARTY_LICENSES.md "dist\ScanPDFStudio\THIRD_PARTY_LICENSES.md" >nul
if errorlevel 1 exit /b 1
xcopy /E /I /Y licenses "dist\ScanPDFStudio\licenses" >nul
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -c "import shutil; shutil.make_archive(r'dist\ScanPDFStudio-portable', 'zip', r'dist\ScanPDFStudio')"
if errorlevel 1 exit /b 1
echo Build complete: dist\ScanPDFStudio and dist\ScanPDFStudio-portable.zip

