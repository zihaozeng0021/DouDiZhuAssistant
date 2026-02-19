@echo off
setlocal
cd /d %~dp0

set "VENV_DIR=.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" -c "import sys" >nul 2>nul
  if errorlevel 1 (
    echo Existing virtual environment is incompatible. Recreating...
    if exist "%VENV_DIR%" (
      rmdir /s /q "%VENV_DIR%"
      if exist "%VENV_DIR%" (
        echo Failed to remove old virtual environment directory: %VENV_DIR%
        pause
        exit /b 1
      )
    )
  )
)

if not exist "%PYTHON_EXE%" (
  echo [1/5] Creating virtual environment...
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv "%VENV_DIR%"
  ) else (
    py -3 -m venv "%VENV_DIR%"
  )
  if errorlevel 1 (
    echo Failed to create virtual environment. Please install Python 3.10/3.11.
    pause
    exit /b 1
  )
)

echo [2/5] Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip --disable-pip-version-check >nul
if errorlevel 1 (
  echo Failed to upgrade pip.
  pause
  exit /b 1
)

if not exist "requirements.txt" (
  echo requirements.txt not found.
  pause
  exit /b 1
)

echo [3/5] Checking dependencies...
"%PYTHON_EXE%" -c "import flask, torch, douzero; from douzero.env.env import get_obs" >nul 2>nul
if errorlevel 1 (
  echo Installing dependencies from requirements.txt...
  "%PYTHON_EXE%" -m pip install -r requirements.txt --disable-pip-version-check
  if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
  )
)

echo [4/5] Checking model files...
if not exist "douzero_WP\landlord.ckpt" (
  echo Missing file: douzero_WP\landlord.ckpt
  pause
  exit /b 1
)
if not exist "douzero_WP\landlord_up.ckpt" (
  echo Missing file: douzero_WP\landlord_up.ckpt
  pause
  exit /b 1
)
if not exist "douzero_WP\landlord_down.ckpt" (
  echo Missing file: douzero_WP\landlord_down.ckpt
  pause
  exit /b 1
)

echo [5/5] Starting DouZero Web Assistant...
start "" "http://127.0.0.1:7860"
"%PYTHON_EXE%" -m app.server
