# AXIOM AI CLI Launcher

**Build AI. Own AI.**

The `@netcore-technologies/axiom-cli` npm package provides a Node.js
launcher for the AXIOM AI command-line interface.

This package is a launcher, not the complete AXIOM AI application.
The Python application must be installed separately.

- Project: https://github.com/NetCore-Technologies/AXIOM-AI
- Issues: https://github.com/NetCore-Technologies/AXIOM-AI/issues
- License: MIT
- Status: Beta

## Requirements

- Node.js 20 or newer.
- Python installed and available on your PATH.
- The AXIOM AI Python application installed in your Python environment.

## Installation

Install the AXIOM Python application:

    python -m pip install axiom-ai

Install the npm launcher:

    npm install --global @netcore-technologies/axiom-cli@beta

Verify the launcher:

    axiom --help

## Quick start

Display available commands:

    axiom --help

Create a project:

    axiom init my-first-ai

Enter the project directory:

    cd my-first-ai

Use the CLI help to discover commands supported by your installed version.

## Updating

Update the npm launcher:

    npm install --global @netcore-technologies/axiom-cli@beta

Update the Python application:

    python -m pip install --upgrade axiom-ai

## Troubleshooting

### The axiom command is not found

Check that npm's global executable directory is on your PATH.
Open a new terminal after changing PATH settings.

### Python cannot be found

Install Python and verify that python --version or python3 --version works.

### AXIOM commands fail

Run axiom --help and report reproducible issues at:

https://github.com/NetCore-Technologies/AXIOM-AI/issues

## Contributing

Contributions and bug reports are welcome. Read the project's
contribution guidelines before opening a pull request:

https://github.com/NetCore-Technologies/AXIOM-AI/blob/main/CONTRIBUTING.md
