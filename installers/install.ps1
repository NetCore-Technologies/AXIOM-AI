$ErrorActionPreference = "Stop"

$Repo = "NetCore-Technologies/AXIOM-AI"
$InstallDir = Join-Path $env:LOCALAPPDATA "AXIOM"
$Exe = Join-Path $InstallDir "AXIOM.exe"

Write-Host "================================="
Write-Host "        AXIOM AI Installer"
Write-Host "================================="
Write-Host ""

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Host "Finding latest AXIOM release..."
$Releases = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases"
$Release = $Releases | Where-Object { -not $_.draft } | Select-Object -First 1

if (-not $Release) {
    throw "Could not find an AXIOM release."
}

$Tag = $Release.tag_name
$Version = $Tag.TrimStart("v")
$Url = "https://github.com/$Repo/releases/download/$Tag/AXIOM-$Version-windows-x64.exe"

Write-Host "Release: $Tag"
Write-Host "Downloading AXIOM..."

Invoke-WebRequest -Uri $Url -OutFile $Exe

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $UserPath) { $UserPath = "" }

if ($UserPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", "User")
}

Write-Host ""
Write-Host "AXIOM installed to $Exe"
Write-Host "Restart your terminal and run: axiom version"
