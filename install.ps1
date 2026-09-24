# The Codex Group — Windows PowerShell One-Liner Installer
# Usage:
#   iwr -useb https://raw.githubusercontent.com/w0tu/codex-cli/main/install.ps1 | iex

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  The Codex Group // CDX Autonomous AI Desktop (Windows)" -ForegroundColor Cyan
Write-Host "  Created by Saad Kashif" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Cyan

$InstallDir = "$env:USERPROFILE\.codex"
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

Write-Host "[1/3] Checking Python installation..." -ForegroundColor Cyan
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[Notice] Python 3 not found in PATH. Please install Python from https://python.org or winget install Python.Python.3.12" -ForegroundColor Yellow
}

Write-Host "[2/3] Cloning/Updating CDX repository..." -ForegroundColor Cyan
$RepoDir = "$InstallDir\codex-cli"
if (Test-Path "$RepoDir\.git") {
    cd $RepoDir
    git pull origin main
} else {
    git clone --depth 1 https://github.com/w0tu/codex-cli.git $RepoDir
}

Write-Host "[3/3] Installing dependencies and creating wrappers..." -ForegroundColor Cyan
pip install -r "$RepoDir\requirements.txt" --quiet

# Create cdx.cmd
$CmdPath = "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\cdx.cmd"
"@echo off`npython -m codex.cli %*" | Out-File -FilePath $CmdPath -Encoding ascii

# Create cdx-app.cmd
$AppCmdPath = "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\cdx-app.cmd"
"@echo off`npython -m codex.app %*" | Out-File -FilePath $AppCmdPath -Encoding ascii

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "  ✓ CDX Installed Successfully on Windows!" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
Write-Host "  Run in PowerShell or CMD: cdx" -ForegroundColor White
Write-Host "  Launch Desktop GUI:       cdx-app" -ForegroundColor White
Write-Host "  Created by Saad Kashif" -ForegroundColor Green
