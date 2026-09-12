# AXIOM Installers

## Linux

Install the latest AXIOM GitHub release:

```bash
curl -fsSL https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.sh | bash
```

The installer places AXIOM in `~/.local/share/axiom` and creates `~/.local/bin/axiom`.

## Windows

Run PowerShell:

```powershell
irm https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.ps1 | iex
```

The executable is installed under `%LOCALAPPDATA%\\AXIOM`.

## Manual downloads

GitHub Releases provide:

- Windows x64 EXE
- Windows portable ZIP
- Linux x64 AppImage
- Linux x64 DEB
- Linux standalone binary

Never store Hugging Face, SuperCompress, or other API credentials in installer files.
