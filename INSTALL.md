# Installation Guide — The Codex Group (`cdx`)

You can install **The Codex Group** on any Debian, Ubuntu, or Linux Mint system using standard `apt`.

---

## Method 1: Direct `apt install` (Recommended)

Download the generated Debian package and install it using `apt`:

```bash
# Clone the repository
git clone https://github.com/w0tu/codex-cli.git
cd codex-cli

# Install directly via apt (resolves all dependencies automatically)
sudo apt install ./dist/cdx_1.7.0_all.deb
```

Or using `dpkg`:
```bash
sudo dpkg -i ./dist/cdx_1.7.0_all.deb
sudo apt install -f  # Fix any missing dependencies if needed
```

---

## Method 2: One-Line Automated Installer

Run the automated installer script:
```bash
curl -sSL https://raw.githubusercontent.com/w0tu/codex-cli/main/install.sh | sudo bash
```

---

## Method 3: Build & Install From Source

```bash
git clone https://github.com/w0tu/codex-cli.git
cd codex-cli

# Build the Debian package
bash build_deb.sh

# Install with apt
sudo apt install ./dist/cdx_1.7.0_all.deb
```

---

## Launching

Once installed, **The Codex Group** is available everywhere on your system:

- **Terminal TUI & CLI**:
  ```bash
  cdx
  ```
- **Standalone Native Desktop Application**:
  ```bash
  cdx-app
  # or
  cdx --app
  ```
- **System Application Menu / Dock**:
  Search for **"The Codex Group"** in your GNOME / KDE / XFCE applications menu.
