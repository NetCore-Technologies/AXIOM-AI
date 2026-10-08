# Installing AXIOM

These scripts install the `axiom` command. AXIOM is operated from the
terminal; the website is not a binary download surface.

## macOS and Linux

<!-- markdownlint-disable MD013 -->
```bash
curl -fsSL https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.sh | bash
```
<!-- markdownlint-enable MD013 -->

The shell installer creates `~/.local/share/axiom` for AXIOM files and links
the command at `~/.local/bin/axiom`.

- On Linux `x86_64`, it downloads the latest release ELF.
- On macOS and non-x86 Linux, it creates an isolated Python environment and
  installs from the repository. Python 3.11+ is required for these
  source-install paths.

If `~/.local/bin` is not already on `PATH`, the installer prints the export
command to add it. Verify the result with:

```bash
axiom version
axiom guide
axiom daemon
```

## Windows PowerShell

<!-- markdownlint-disable MD013 -->
```powershell
irm https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.ps1 | iex
```
<!-- markdownlint-enable MD013 -->

The PowerShell installer downloads the latest non-draft Windows release to
`%LOCALAPPDATA%\AXIOM\AXIOM.exe` and adds `%LOCALAPPDATA%\AXIOM` to the user
`PATH`. Restart PowerShell before verifying:

```powershell
axiom version
axiom guide
axiom daemon
```

## After installation

Start a local project and validate its scaffold:

```bash
axiom init my-ai
cd my-ai
axiom project validate
axiom config validate
```

For the model, dataset, training-plan, and MCP examples, see the
[first five minutes](../README.md#first-five-minutes) section in the root
README.

The installers never contain Hugging Face, SuperCompress, or other API
credentials. Configure those integrations through AXIOM after installation.

`axiom daemon` binds to loopback and asks the operating system for a free
port. It prints the URL for local scripts; stop it with Ctrl-C.
