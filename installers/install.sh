#!/usr/bin/env bash
set -euo pipefail

REPO="NetCore-Technologies/AXIOM-AI"
INSTALL_DIR="${HOME}/.local/share/axiom"
BIN_DIR="${HOME}/.local/bin"

echo "================================="
echo "        AXIOM AI Installer"
echo "================================="
echo

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required."
  exit 1
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

echo "Finding latest AXIOM release..."
RELEASE_JSON="$(curl -fsSL "https://api.github.com/repos/$REPO/releases")"

TAG="$(printf "%s" "$RELEASE_JSON" | grep -m1 "\"tag_name\"" | sed -E "s/.*\"tag_name\": \"([^\"]+)\".*/\\1/")"

if [ -z "$TAG" ]; then
  echo "Error: could not determine an AXIOM release."
  exit 1
fi

VERSION="${TAG#v}"
ASSET="AXIOM-${VERSION}-linux-x64"
URL="https://github.com/$REPO/releases/download/$TAG/$ASSET"

echo "Release: $TAG"
echo "Downloading AXIOM..."

curl -fL "$URL" -o "$INSTALL_DIR/axiom"
chmod +x "$INSTALL_DIR/axiom"
ln -sf "$INSTALL_DIR/axiom" "$BIN_DIR/axiom"

echo
echo "AXIOM installed to: $INSTALL_DIR"
echo

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "Add AXIOM to your PATH with:"
  echo
  echo "  export PATH=\"$HOME/.local/bin:\$PATH\""
  echo
fi

"$INSTALL_DIR/axiom" version
