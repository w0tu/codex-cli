#!/usr/bin/env bash
# The Codex Group — Universal Cross-Platform Installer (Linux, macOS, WSL)
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/w0tu/codex-cli/main/install.sh | bash
#   or with sudo:
#   curl -fsSL https://raw.githubusercontent.com/w0tu/codex-cli/main/install.sh | sudo bash

set -e

CYAN="\033[1;36m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

echo -e "${CYAN}=====================================================${RESET}"
echo -e "${CYAN}  The Codex Group // CDX Autonomous AI Desktop & CLI  ${RESET}"
echo -e "${CYAN}  Created by Saad Kashif                              ${RESET}"
echo -e "${CYAN}=====================================================${RESET}"

OS="$(uname -s)"
ARCH="$(uname -m)"
IS_ROOT=0
if [ "$EUID" -eq 0 ]; then
    IS_ROOT=1
fi

echo -e "${CYAN}[Info]${RESET} Detected Platform: ${GREEN}${OS} (${ARCH})${RESET} | Root: ${GREEN}$([ $IS_ROOT -eq 1 ] && echo 'Yes' || echo 'No')${RESET}"

# ──────────────────────────────────────────────────────────
# 1. LINUX DEBIAN / UBUNTU (WITH ROOT / APT)
# ──────────────────────────────────────────────────────────
if [ "$OS" = "Linux" ] && [ $IS_ROOT -eq 1 ] && command -v apt-get >/dev/null 2>&1; then
    echo -e "${CYAN}[Step 1/3]${RESET} Updating apt repositories and prerequisites..."
    apt-get update -qq || true
    apt-get install -y -qq python3 python3-pip curl xdotool || true

    DEB_URL="https://github.com/w0tu/codex-cli/releases/latest/download/cdx_1.7.0_all.deb"
    TMP_DEB="/tmp/cdx_1.7.0_all.deb"
    
    echo -e "${CYAN}[Step 2/3]${RESET} Downloading and installing cdx Debian package via apt..."
    curl -fsSL "$DEB_URL" -o "$TMP_DEB" || true

    if [ -f "$TMP_DEB" ] && [ -s "$TMP_DEB" ]; then
        # Use ./ with apt install so apt resolves dependencies natively
        apt-get install -y "$TMP_DEB"
        rm -f "$TMP_DEB"
    else
        echo -e "${YELLOW}[Notice]${RESET} Installing from local / python source..."
        pip3 install --break-system-packages -e . || pip3 install -e .
    fi

    echo -e "${CYAN}[Step 3/3]${RESET} Updating desktop database..."
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database /usr/share/applications || true
    fi

# ──────────────────────────────────────────────────────────
# 2. LINUX NON-ROOT (USER SPACE INSTALL ~/.local/bin)
# ──────────────────────────────────────────────────────────
elif [ "$OS" = "Linux" ] && [ $IS_ROOT -eq 0 ]; then
    echo -e "${CYAN}[Info]${RESET} Installing in user-space (${HOME}/.local)..."
    mkdir -p "$HOME/.local/bin" "$HOME/.local/share/cdx"

    # Clone or fetch source if running standalone
    INSTALL_DIR="$HOME/.local/share/cdx/repo"
    if [ ! -d "$INSTALL_DIR" ]; then
        git clone --depth 1 https://github.com/w0tu/codex-cli.git "$INSTALL_DIR" || true
    fi

    # Create cdx wrapper in ~/.local/bin/cdx
    cat << 'WRAPPER' > "$HOME/.local/bin/cdx"
#!/usr/bin/env bash
python3 -m codex.cli "$@"
WRAPPER
    chmod +x "$HOME/.local/bin/cdx"

    # Create cdx-app wrapper
    cat << 'WRAPPER' > "$HOME/.local/bin/cdx-app"
#!/usr/bin/env bash
python3 -m codex.app "$@"
WRAPPER
    chmod +x "$HOME/.local/bin/cdx-app"

    # Ensure ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        export PATH="$HOME/.local/bin:$PATH"
        SHELL_RC="$HOME/.bashrc"
        [ -n "$ZSH_VERSION" ] && SHELL_RC="$HOME/.zshrc"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    fi

# ──────────────────────────────────────────────────────────
# 3. MACOS (HOMEBREW / PYTHON3)
# ──────────────────────────────────────────────────────────
elif [ "$OS" = "Darwin" ]; then
    echo -e "${CYAN}[macOS]${RESET} Setting up CDX for macOS..."
    mkdir -p "$HOME/.local/bin"

    # Create wrapper scripts
    cat << 'WRAPPER' > "$HOME/.local/bin/cdx"
#!/usr/bin/env bash
python3 -m codex.cli "$@"
WRAPPER
    chmod +x "$HOME/.local/bin/cdx"

    cat << 'WRAPPER' > "$HOME/.local/bin/cdx-app"
#!/usr/bin/env bash
python3 -m codex.app "$@"
WRAPPER
    chmod +x "$HOME/.local/bin/cdx-app"

    # Ensure in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        export PATH="$HOME/.local/bin:$PATH"
        SHELL_RC="$HOME/.zshrc"
        [ -f "$HOME/.bash_profile" ] && SHELL_RC="$HOME/.bash_profile"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    fi
fi

echo -e ""
echo -e "${GREEN}=====================================================${RESET}"
echo -e "${GREEN}  ✓ CDX Installed Successfully!                     ${RESET}"
echo -e "${GREEN}=====================================================${RESET}"
echo -e "  To start CLI:         ${CYAN}cdx${RESET}"
echo -e "  To launch Desktop UI: ${CYAN}cdx-app${RESET} (or open http://127.0.0.1:4545)"
echo -e "  Created by:           ${GREEN}Saad Kashif${RESET}"
echo -e "  GitHub:               ${CYAN}https://github.com/w0tu/codex-cli${RESET}"
echo -e ""
