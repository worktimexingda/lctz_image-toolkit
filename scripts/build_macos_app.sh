#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="lctz_image-toolkit"
TARGET_ARCH="${1:-native}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must be run on macOS."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

PYINSTALLER_ARGS=(
  --noconfirm
  --clean
  --windowed
  --name "$APP_NAME"
  lctz_image_toolkit.py
)

if [[ "$TARGET_ARCH" != "native" ]]; then
  PYINSTALLER_ARGS+=(--target-arch "$TARGET_ARCH")
fi

python -m PyInstaller "${PYINSTALLER_ARGS[@]}"

if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "dist/${APP_NAME}.app"
fi

ZIP_NAME="dist/${APP_NAME}-macos-${TARGET_ARCH}-$(uname -m).zip"
ditto -c -k --keepParent "dist/${APP_NAME}.app" "$ZIP_NAME"

echo
echo "Build finished:"
echo "  dist/${APP_NAME}.app"
echo "  ${ZIP_NAME}"
