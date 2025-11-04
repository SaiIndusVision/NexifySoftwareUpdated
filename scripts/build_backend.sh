#!/usr/bin/env bash
set -euo pipefail

# Build Django backend into a single native binary using Nuitka
# Uses an isolated virtualenv to avoid system package restrictions (PEP 668)

ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found" >&2
  exit 1
fi

VENV_DIR=".backend_build_venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "Installing build dependencies in venv (Nuitka + zstd, ordered-set)..."
"$PIP" install --upgrade pip >/dev/null
"$PIP" install --upgrade "nuitka[zstd]" "ordered-set>=4.1.0" >/dev/null

OUT_DIR="backend_build"
BIN_NAME="nexify_backend"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo "Compiling Django backend with Nuitka..."
"$PY" -m nuitka \
  --standalone \
  --onefile \
  --assume-yes-for-downloads \
  --nofollow-import-to=tkinter,tests \
  --enable-plugin=pylint-warnings \
  --output-dir="$OUT_DIR" \
  --output-filename="$BIN_NAME" \
  django-backend/manage.py

echo "Backend binary created at: $OUT_DIR/$BIN_NAME (or .exe on Windows)"

exit 0


