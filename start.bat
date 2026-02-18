@echo off
setlocal
cd /d %~dp0

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
  set "PYTHON_EXE=python"
)

echo Starting DouZero Web Assistant...
start "" "http://127.0.0.1:7860"
"%PYTHON_EXE%" -m app.server

