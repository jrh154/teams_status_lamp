<#
.SYNOPSIS
    Builds and packages the Teams Status Lamp application.

.DESCRIPTION
    This script automates the process of:
    1. Cleaning previous build artifacts.
    2. Building the executable using PyInstaller.
    3. Creating a versioned package folder.
    4. Copying the executable, README, and LICENSE.
    5. Zipping the package for release.

.PARAMETER Version
    The version string for the release (e.g., "2025.3.1").

.EXAMPLE
    .\build_release.ps1 -Version "2025.3.1"
#>

param (
    [Parameter(Mandatory=$true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"

Write-Host "Starting build for version $Version..."

# 1. Clean previous builds
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "*.spec") { Remove-Item -Force "*.spec" }

# 2. Build Executable
Write-Host "Building EXE with PyInstaller..."
python -m PyInstaller --noconsole --onefile --icon="install_files/tray_icon.png" --add-data "install_files;install_files" --hidden-import="pystray" teams_status_control.py

if (-not (Test-Path "dist\teams_status_control.exe")) {
    Write-Error "Build failed! Exe not found."
    exit 1
}

# 3. Create Package Folder
$PackageName = "teams_lamp_$Version"
if (Test-Path $PackageName) { Remove-Item -Recurse -Force $PackageName }
New-Item -ItemType Directory -Force -Path $PackageName | Out-Null

# 4. Copy Files
Write-Host "Copying files..."
Copy-Item "dist\teams_status_control.exe" -Destination $PackageName
Copy-Item "..\README.md" -Destination $PackageName

# Copy License if it exists
if (Test-Path "install_files\LICENSE") {
    Copy-Item "install_files\LICENSE" -Destination $PackageName
}

# Copy Firmware
if (Test-Path "..\lamp_firmware") {
    Write-Host "Copying firmware..."
    Copy-Item "..\lamp_firmware" -Destination $PackageName -Recurse
}

# 5. Zip
Write-Host "Zipping package..."
$ReleaseDir = "..\Releases"
if (-not (Test-Path $ReleaseDir)) { New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null }

$ZipName = "$ReleaseDir\teams_lamp_$Version.zip"
if (Test-Path $ZipName) { Remove-Item -Force $ZipName }
Compress-Archive -Path "$PackageName\*" -DestinationPath $ZipName -Force

Write-Host "Build Complete! Package created: $ZipName"

# 6. Cleanup
Write-Host "Cleaning up temporary files..."
if (Test-Path $PackageName) { Remove-Item -Recurse -Force $PackageName }
