#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Building a universal2 macOS app."
echo "This requires a universal2 Python build and universal2-compatible dependency wheels."
echo

"$ROOT_DIR/scripts/build_macos_app.sh" universal2
