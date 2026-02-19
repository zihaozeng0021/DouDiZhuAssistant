@echo off
setlocal
cd /d %~dp0

set "VENV_DIR=.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Virtual environment not found: %PYTHON_EXE%
  echo Please run start.bat first.
  exit /b 1
)

echo [1/3] Installing PyInstaller...
"%PYTHON_EXE%" -m pip install --upgrade pyinstaller --disable-pip-version-check
if errorlevel 1 (
  echo Failed to install PyInstaller.
  exit /b 1
)

echo [2/3] Building single-file executable...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

"%PYTHON_EXE%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --name "DouDiZhuAssistant" ^
  --add-data "app\templates;app\templates" ^
  --add-data "app\static;app\static" ^
  --add-data "douzero_WP;douzero_WP" ^
  --collect-all douzero ^
  --collect-all flask ^
  launch_exe.py
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo [3/3] Build complete:
echo dist\DouDiZhuAssistant.exe
exit /b 0
