#!/usr/bin/env bash

set -u

pause_and_exit() {
  echo "$1"
  printf "Press Enter to exit..."
  read -r _
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

VENV_DIR=".venv"
PYTHON_EXE="$VENV_DIR/bin/python"

if [[ -x "$PYTHON_EXE" ]]; then
  if ! "$PYTHON_EXE" -c "import sys" >/dev/null 2>&1; then
    echo "Existing virtual environment is incompatible. Recreating..."
    rm -rf "$VENV_DIR" || pause_and_exit "Failed to remove old virtual environment directory: $VENV_DIR"
  fi
fi

if [[ ! -x "$PYTHON_EXE" ]]; then
  echo "[1/5] Creating virtual environment..."
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$VENV_DIR" || pause_and_exit "Failed to create virtual environment. Please install Python 3.10/3.11."
  elif command -v python >/dev/null 2>&1; then
    python -m venv "$VENV_DIR" || pause_and_exit "Failed to create virtual environment. Please install Python 3.10/3.11."
  else
    pause_and_exit "Python was not found. Please install Python 3.10/3.11."
  fi
fi

echo "[2/5] Upgrading pip..."
"$PYTHON_EXE" -m pip install --upgrade pip --disable-pip-version-check >/dev/null \
  || pause_and_exit "Failed to upgrade pip."

if [[ ! -f "requirements.txt" ]]; then
  pause_and_exit "requirements.txt not found."
fi

echo "[3/5] Checking dependencies..."
if ! "$PYTHON_EXE" -c "import flask, torch, douzero; from douzero.env.env import get_obs" >/dev/null 2>&1; then
  echo "Installing dependencies from requirements.txt..."
  "$PYTHON_EXE" -m pip install -r requirements.txt --disable-pip-version-check \
    || pause_and_exit "Dependency installation failed."
fi

echo "[4/5] Checking model files..."
for model in \
  "douzero_WP/landlord.ckpt" \
  "douzero_WP/landlord_up.ckpt" \
  "douzero_WP/landlord_down.ckpt"
do
  [[ -f "$model" ]] || pause_and_exit "Missing file: $model"
done

echo "[5/5] Starting DouZero Web Assistant..."
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:7860" >/dev/null 2>&1 || true
elif command -v gio >/dev/null 2>&1; then
  gio open "http://127.0.0.1:7860" >/dev/null 2>&1 || true
fi

"$PYTHON_EXE" -m app.server || pause_and_exit "Server exited unexpectedly."
