#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  miktag — Linux build script
#  Run from the project root:  bash build_linux.sh
#  Requires: Python 3.11+, pip
#  Optional: dpkg-deb (for .deb), fakeroot
# ─────────────────────────────────────────────────────────────────────────────
set -e

APP="miktag"
VERSION="1.0.0"
ARCH="amd64"
DEB_ROOT="deb_pkg"

echo ""
echo " [1/4] Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo " [2/4] Building with PyInstaller..."
pyinstaller miktag.spec --clean --noconfirm

echo " [3/4] Build complete!  Output: dist/miktag/miktag"

# ── Create .deb package ─────────────────────────────────────────────────────
if command -v dpkg-deb &>/dev/null; then
    echo " [4/4] Building .deb package..."
    mkdir -p installer

    # Directory structure for .deb
    rm -rf "$DEB_ROOT"
    mkdir -p "$DEB_ROOT/DEBIAN"
    mkdir -p "$DEB_ROOT/opt/$APP"
    mkdir -p "$DEB_ROOT/usr/share/applications"
    mkdir -p "$DEB_ROOT/usr/share/pixmaps"
    mkdir -p "$DEB_ROOT/usr/local/bin"

    # Copy PyInstaller output
    cp -r dist/$APP/* "$DEB_ROOT/opt/$APP/"

    # Symlink so users can run `miktag` from terminal
    ln -sf "/opt/$APP/$APP" "$DEB_ROOT/usr/local/bin/$APP"

    # .desktop file (shows in app launcher with icon)
    cat > "$DEB_ROOT/usr/share/applications/$APP.desktop" << DESKTOP
[Desktop Entry]
Name=miktag
Comment=Automatic music tagger powered by Shazam
Exec=/opt/$APP/$APP
Icon=/opt/$APP/assets/icon.png
Terminal=false
Type=Application
Categories=Audio;Music;
Keywords=music;tag;id3;shazam;
DESKTOP

    # Copy icon
    if [ -f assets/icon.png ]; then
        cp assets/icon.png "$DEB_ROOT/usr/share/pixmaps/$APP.png"
    fi

    # Control file (package metadata)
    cat > "$DEB_ROOT/DEBIAN/control" << CONTROL
Package: $APP
Version: $VERSION
Architecture: $ARCH
Maintainer: miktag <contact@miktag.app>
Description: Automatic music tagger powered by Shazam
 miktag identifies your music files using Shazam and writes
 ID3/FLAC/MP4 tags automatically. Includes album art download
 and automatic file organization.
Depends: libgtk-3-0 | libqt5webkit5
Homepage: https://github.com/yourname/miktag
CONTROL

    # Set permissions
    chmod 755 "$DEB_ROOT/opt/$APP/$APP"
    find "$DEB_ROOT" -type d -exec chmod 755 {} \;

    # Build the .deb
    fakeroot dpkg-deb --build "$DEB_ROOT" \
        "installer/${APP}_${VERSION}_${ARCH}.deb"

    rm -rf "$DEB_ROOT"
    echo " Installer saved to: installer/${APP}_${VERSION}_${ARCH}.deb"
    echo " Install with:  sudo dpkg -i installer/${APP}_${VERSION}_${ARCH}.deb"
else
    echo " [4/4] dpkg-deb not found — skipping .deb creation."
    echo "       Install with:  sudo apt install dpkg fakeroot"
    echo ""
    echo "       You can run the app directly:  ./dist/miktag/miktag"
fi

echo ""
echo " Done!"
