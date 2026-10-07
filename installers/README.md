# AXIOM Installers

## macOS and Linux

Install the latest AXIOM GitHub release:

```bash
curl -fsSL https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.sh | bash
```

The installer places AXIOM in `~/.local/share/axiom` and creates `~/.local/bin/axiom`. macOS and non-x86 Linux systems install the CLI from the repository in an isolated Python environment.

## Windows

Run PowerShell:

```powershell
irm https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.ps1 | iex
```

The executable is installed under `%LOCALAPPDATA%\\AXIOM`.

The website intentionally has no binary download links. Use these terminal installers so the CLI is the entry point.

Never store Hugging Face, SuperCompress, or other API credentials in installer files.
