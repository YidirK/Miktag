#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  miktag — macOS build script
#  Run from the project root:  bash build_macos.sh
#  Requires: Python 3.11+, pip, Xcode CLI tools
#  Optional: create-dmg  (brew install create-dmg)
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo ""
echo " [1/4] Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo " [2/4] Building with PyInstaller..."
pyinstaller miktag.spec --clean --noconfirm

echo " [3/4] Build complete!  Output: dist/miktag.app"

# ── Optional: wrap in a .dmg installer ──────────────────────────────────────
if command -v create-dmg &>/dev/null; then
    echo " [4/4] Creating .dmg with create-dmg..."
    mkdir -p installer
    create-dmg \
        --volname "miktag" \
        --volicon "assets/icon.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "miktag.app" 175 190 \
        --hide-extension "miktag.app" \
        --app-drop-link 425 190 \
        "installer/miktag-macos.dmg" \
        "dist/miktag.app"
    echo " Installer saved to: installer/miktag-macos.dmg"
else
    echo " [4/4] create-dmg not found — skipping .dmg creation."
    echo "       Install with:  brew install create-dmg"
    echo "       Then re-run this script."
    echo ""
    echo "       Alternatively, drag dist/miktag.app to your Applications folder."
fi

# ── Optional: ad-hoc code sign (needed on Apple Silicon) ───────────────────
echo ""
echo " Applying ad-hoc code signature (Apple Silicon compatibility)..."
codesign --force --deep --sign - dist/miktag.app 2>/dev/null || true

echo ""
echo " Done!  Launch with:  open dist/miktag.app"
