# 📦 Universal Installation Guide — The Codex Group (`cdx`)

Created by **Saad Kashif**. `cdx` runs natively across **Linux**, **macOS**, and **Windows**.

---

## ⚡ Instant 1-Liner Install (Recommended for All Platforms)

### 🐧 Linux & 🍎 macOS:
```bash
curl -fsSL https://raw.githubusercontent.com/w0tu/codex-cli/main/install.sh | bash
```
> *Runs seamlessly in user-space (`~/.local/bin`) or system-wide if run with `sudo`.*

### 🪟 Windows (PowerShell):
```powershell
iwr -useb https://raw.githubusercontent.com/w0tu/codex-cli/main/install.ps1 | iex
```

---

## 🐧 Linux (Ubuntu / Debian / Mint)

### Why did `sudo apt install cdx` fail?
`apt` only queries official Ubuntu/Debian archive mirrors. A third-party `.deb` package cannot be found by package name alone until registered.

### Fix 1: Register and Install with One Command
Run the APT setup script which automatically registers and installs `cdx`:
```bash
curl -fsSL https://raw.githubusercontent.com/w0tu/codex-cli/main/setup-apt.sh | sudo bash
```

### Fix 2: Direct Local `.deb` Installation via APT
If you download or clone the `.deb` file, **you must include `./`** so `apt` knows to treat it as a local file:
```bash
# Correct syntax with leading ./
sudo apt install ./dist/cdx_1.7.0_all.deb

# Or with dpkg
sudo dpkg -i dist/cdx_1.7.0_all.deb
sudo apt install -f -y
```

### Arch Linux (AUR / Makepkg):
```bash
git clone https://github.com/w0tu/codex-cli.git
cd codex-cli
pip install -e .
```

---

## 🍎 macOS (Apple Silicon M1/M2/M3 & Intel)

### Option 1: Automatic 1-Liner
```bash
curl -fsSL https://raw.githubusercontent.com/w0tu/codex-cli/main/install.sh | bash
```

### Option 2: Manual via Homebrew & Python
```bash
# Ensure Python 3 is installed
brew install python3

# Clone and install
git clone https://github.com/w0tu/codex-cli.git
cd codex-cli
pip3 install -e .

# Launch
cdx
```

---

## 🪟 Windows (PowerShell & WSL2)

### Option 1: Native Windows via PowerShell
Open PowerShell as Administrator:
```powershell
iwr -useb https://raw.githubusercontent.com/w0tu/codex-cli/main/install.ps1 | iex
```
This automatically sets up `cdx.cmd` and `cdx-app.cmd` in your `%LOCALAPPDATA%\Microsoft\WindowsApps` path.

### Option 2: Windows Subsystem for Linux (WSL2) — Highest Performance
Open your WSL2 terminal (Ubuntu) and run:
```bash
curl -fsSL https://raw.githubusercontent.com/w0tu/codex-cli/main/install.sh | bash
```

---

## 🚀 Running & Verification

Once installed, the following commands are available globally:

| Command | Description |
|---|---|
| `cdx` | Launch the ultra-low-latency interactive terminal AI coding assistant |
| `cdx-app` | Launch the standalone dark-mode GUI Desktop Application (`http://127.0.0.1:4545`) |
| `cdx swarm "directive"` | Execute autonomous 4-node multi-agent swarm synthesis |
| `cdx --version` | Display current installed version (`v1.7.0`) |

---

## 🌐 Official Cloudflare Pages Site
Visit [https://codexgroup.pages.dev](https://codexgroup.pages.dev) for interactive playgrounds, live benchmarks, and docs.
