#!/usr/bin/env bash
set -euo pipefail

REPO="NetCore-Technologies/AXIOM-AI"
INSTALL_DIR="${HOME}/.local/share/axiom"
BIN_DIR="${HOME}/.local/bin"

echo "AXIOM terminal installer"
echo
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

case "$(uname -s)" in
  Darwin)
    command -v python3 >/dev/null 2>&1 || { echo "Error: Python 3.11+ is required."; exit 1; }
    echo "Installing the latest AXIOM CLI from GitHub..."
    python3 -m venv "$INSTALL_DIR/venv"
    "$INSTALL_DIR/venv/bin/python" -m pip install --upgrade pip >/dev/null
    "$INSTALL_DIR/venv/bin/python" -m pip install --upgrade "git+https://github.com/$REPO.git@main"
    ln -sf "$INSTALL_DIR/venv/bin/axiom" "$BIN_DIR/axiom"
    AXIOM_BIN="$INSTALL_DIR/venv/bin/axiom"
    ;;
  Linux)
    command -v curl >/dev/null 2>&1 || { echo "Error: curl is required."; exit 1; }
    ARCH="$(uname -m)"
    if [ "$ARCH" = "x86_64" ]; then
      echo "Finding the latest AXIOM Linux release..."
      RELEASE_JSON="$(curl -fsSL "https://api.github.com/repos/$REPO/releases")"
      TAG="$(printf "%s" "$RELEASE_JSON" | grep -m1 '"tag_name"' | sed -E 's/.*"tag_name": "([^"]+)".*/\1/')"
      [ -n "$TAG" ] || { echo "Error: could not determine an AXIOM release."; exit 1; }
      ASSET="AXIOM-${TAG}-linux-x64.elf"
      echo "Installing $TAG..."
      curl -fL "https://github.com/$REPO/releases/download/$TAG/$ASSET" -o "$INSTALL_DIR/axiom"
      chmod +x "$INSTALL_DIR/axiom"
      ln -sf "$INSTALL_DIR/axiom" "$BIN_DIR/axiom"
      AXIOM_BIN="$INSTALL_DIR/axiom"
    else
      echo "No native Linux binary is published for $ARCH. Installing from source..."
      command -v python3 >/dev/null 2>&1 || { echo "Error: Python 3.11+ is required."; exit 1; }
      python3 -m venv "$INSTALL_DIR/venv"
      "$INSTALL_DIR/venv/bin/python" -m pip install --upgrade pip >/dev/null
      "$INSTALL_DIR/venv/bin/python" -m pip install --upgrade "git+https://github.com/$REPO.git@main"
      ln -sf "$INSTALL_DIR/venv/bin/axiom" "$BIN_DIR/axiom"
      AXIOM_BIN="$INSTALL_DIR/venv/bin/axiom"
    fi
    ;;
  *)
    echo "Error: unsupported operating system. Use the PowerShell installer on Windows."
    exit 1
    ;;
esac

echo
echo "AXIOM installed."
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "Add it to your PATH with:"
  echo "  export PATH=\"$HOME/.local/bin:\$PATH\""
fi
echo
"$AXIOM_BIN" version
