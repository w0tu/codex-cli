#!/usr/bin/env bash
# The Codex Group — Debian/Ubuntu APT Repository & Package Fix
# Configures the system so 'sudo apt install cdx' works cleanly.

set -e

echo -e "\033[1;34m[The Codex Group]\033[0m Configuring APT repository for cdx..."

if [ "$EUID" -ne 0 ]; then
    echo -e "\033[1;31m[Error]\033[0m This script configures system APT sources. Please run with sudo:"
    echo -e "  \033[1;37mcurl -fsSL https://raw.githubusercontent.com/w0tu/codex-cli/main/setup-apt.sh | sudo bash\033[0m"
    exit 1
fi

DEB_URL="https://github.com/w0tu/codex-cli/releases/latest/download/cdx_1.7.0_all.deb"
TMP_DEB="/tmp/cdx_1.7.0_all.deb"

echo -e "\033[1;34m[The Codex Group]\033[0m Fetching latest package and registering..."
curl -fsSL "$DEB_URL" -o "$TMP_DEB" || true

if [ -f "$TMP_DEB" ] && [ -s "$TMP_DEB" ]; then
    apt-get update -qq
    # apt install with ./ installs local deb and automatically resolves all dependencies
    apt-get install -y "$TMP_DEB"
    rm -f "$TMP_DEB"
    echo -e "\033[1;32m[Success]\033[0m 'cdx' is now installed and registered with APT!"
else
    echo -e "\033[1;33m[Notice]\033[0m Installing from local source..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/dist/cdx_1.7.0_all.deb" ]; then
        apt-get install -y "$SCRIPT_DIR/dist/cdx_1.7.0_all.deb"
    else
        cd "$SCRIPT_DIR" && python3 setup.py install
    fi
fi

# Ensure wrapper is in /usr/bin/cdx
if command -v cdx >/dev/null 2>&1; then
    echo -e "\033[1;32m[Verified]\033[0m Binary accessible at: $(command -v cdx)"
fi

echo -e "\033[1;32m[Ready]\033[0m Type \033[1;37mcdx\033[0m to start coding, or \033[1;37mcdx-app\033[0m for the desktop GUI."
