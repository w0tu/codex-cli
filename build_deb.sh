#!/usr/bin/env bash
set -e

VERSION="1.7.0"
PKG_DIR="dist/cdx_${VERSION}_all"

echo "Building Debian package for cdx v${VERSION}..."
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/cdx"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor/scalable/apps"

# 1. Control File
cat << 'CTRL' > "$PKG_DIR/DEBIAN/control"
Package: cdx
Version: 1.7.0
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), xdotool
Recommends: nodejs, npm
Maintainer: The Codex Group <dev@codex.group>
Homepage: https://github.com/w0tu/codex-cli
Description: The Codex Group — Autonomous AI Desktop & Terminal
 Autonomous AI coding agent, native OLED desktop application,
 hardware-accelerated Groq LPU streaming, desktop mouse control,
 and Google Antigravity delegation bridge.
CTRL

# 2. Post-installation script
cat << 'POSTINST' > "$PKG_DIR/DEBIAN/postinst"
#!/bin/sh
set -e
chmod +x /usr/bin/cdx
chmod +x /usr/bin/cdx-app
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
exit 0
POSTINST
chmod 755 "$PKG_DIR/DEBIAN/postinst"

# 3. Clean local pycache and copy application files excluding pycache & node_modules
find codex -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
cp -r codex "$PKG_DIR/usr/share/cdx/"
rm -rf "$PKG_DIR/usr/share/cdx/codex/electron/node_modules"
find "$PKG_DIR" -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
cp setup.py pyproject.toml README.md "$PKG_DIR/usr/share/cdx/"

# 4. Binaries /usr/bin/cdx and /usr/bin/cdx-app
cat << 'BIN' > "$PKG_DIR/usr/bin/cdx"
#!/usr/bin/env bash
export PYTHONPATH="/usr/share/cdx:$PYTHONPATH"
exec python3 -m codex.main "$@"
BIN
chmod 755 "$PKG_DIR/usr/bin/cdx"

cat << 'APPBIN' > "$PKG_DIR/usr/bin/cdx-app"
#!/usr/bin/env bash
export PYTHONPATH="/usr/share/cdx:$PYTHONPATH"
exec python3 -m codex.main --app "$@"
APPBIN
chmod 755 "$PKG_DIR/usr/bin/cdx-app"

# 5. Desktop Entry & Icon
cat << 'DSK' > "$PKG_DIR/usr/share/applications/cdx.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=The Codex Group
GenericName=Autonomous AI Desktop
Comment=Hardware-accelerated AI Copilot, Desktop Automation & Antigravity
Exec=/usr/bin/cdx-app
Icon=cdx
Terminal=false
Categories=Development;Utility;IDE;
StartupWMClass=TheCodexGroup
StartupNotify=true
DSK

cp ~/.local/share/icons/codex.svg "$PKG_DIR/usr/share/icons/hicolor/scalable/apps/cdx.svg"

# 6. Build the .deb archive
dpkg-deb --build --root-owner-group "$PKG_DIR" "dist/cdx_${VERSION}_all.deb"
echo "Package successfully generated: dist/cdx_${VERSION}_all.deb"
