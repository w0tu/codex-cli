#!/usr/bin/env bash
# The Codex Group — Universal Debian/Ubuntu Installation Script
# Allows anyone to install via: curl -sSL https://raw.githubusercontent.com/w0tu/codex-cli/main/install.sh | sudo bash
# Or directly via: sudo apt install ./dist/cdx_1.7.0_all.deb

set -e

echo -e "\033[1;34m[The Codex Group]\033[0m Initializing installation..."

# Ensure root
if [ "$EUID" -ne 0 ]; then
    echo -e "\033[1;31m[Error]\033[0m Please run as root: sudo bash install.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEB_FILE="$SCRIPT_DIR/dist/cdx_1.7.0_all.deb"

# 1. Update and install prerequisites
apt-get update -qq
apt-get install -y -qq python3 python3-pip xdotool

# 2. If deb package is present locally, install directly via apt
if [ -f "$DEB_FILE" ]; then
    echo -e "\033[1;32m[The Codex Group]\033[0m Installing cdx package via apt..."
    apt-get install -y "$DEB_FILE"
else
    # Download latest release deb from GitHub
    TMP_DEB="/tmp/cdx_latest.deb"
    echo -e "\033[1;34m[The Codex Group]\033[0m Downloading latest cdx release..."
    curl -sSL "https://github.com/w0tu/codex-cli/releases/latest/download/cdx_1.7.0_all.deb" -o "$TMP_DEB" || true
    if [ -f "$TMP_DEB" ]; then
        apt-get install -y "$TMP_DEB"
        rm -f "$TMP_DEB"
    else
        echo -e "\033[1;33m[Notice]\033[0m Building and installing from local source..."
        cd "$SCRIPT_DIR" && bash build_deb.sh
        apt-get install -y "$DEB_FILE"
    fi
fi

# 3. Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi

echo -e "\033[1;32m[Success]\033[0m The Codex Group (cdx) installed successfully!"
echo -e "Run in terminal:    \033[1;37mcdx\033[0m"
echo -e "Launch desktop app: \033[1;37mcdx-app\033[0m"
