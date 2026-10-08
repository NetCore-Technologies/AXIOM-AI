#!/usr/bin/env bash
set -euo pipefail

REPO="NetCore-Technologies/AXIOM-AI"
INSTALL_DIR="${HOME}/.local/share/axiom"
BIN_DIR="${HOME}/.local/bin"
DOWNLOAD_DIR=""

cleanup_download() {
  if [[ -n "$DOWNLOAD_DIR" ]]; then
    rm -rf -- "$DOWNLOAD_DIR"
  fi
}

trap cleanup_download EXIT

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "Error: sha256sum or shasum is required to verify the release." >&2
    return 1
  fi
}

latest_release_tag() {
  curl -fsSL --retry 3 "https://api.github.com/repos/$REPO/releases?per_page=20" \
    | sed -nE '/"tag_name"[[:space:]]*:/ { s/.*"tag_name"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/; p; q; }'
}

install_linux_bundle() {
  local tag="$1"
  local asset="AXIOM-${tag}-linux-x64.tar.gz"
  local download_base="https://github.com/$REPO/releases/download/$tag"
  local release_dir="$INSTALL_DIR/releases/$tag"
  local extracted_dir

  DOWNLOAD_DIR="$(mktemp -d "$INSTALL_DIR/.download.XXXXXX")"
  echo "Downloading the efficient Linux bundle ($tag)..."
  curl -fL --retry 3 "$download_base/$asset" -o "$DOWNLOAD_DIR/$asset"
  curl -fL --retry 3 "$download_base/SHA256SUMS" -o "$DOWNLOAD_DIR/SHA256SUMS"

  local expected actual
  expected="$(awk -v asset="$asset" '$2 == asset { print $1; exit }' "$DOWNLOAD_DIR/SHA256SUMS")"
  [[ "$expected" =~ ^[[:xdigit:]]{64}$ ]] || {
    echo "Error: the release checksum does not list $asset." >&2
    return 1
  }
  actual="$(sha256_file "$DOWNLOAD_DIR/$asset")"
  [[ "$actual" == "$expected" ]] || {
    echo "Error: checksum verification failed for $asset." >&2
    return 1
  }

  extracted_dir="$DOWNLOAD_DIR/extracted"
  mkdir -p "$extracted_dir" "$INSTALL_DIR/releases"
  tar -xzf "$DOWNLOAD_DIR/$asset" -C "$extracted_dir"
  [[ -x "$extracted_dir/AXIOM/AXIOM" ]] || {
    echo "Error: the Linux bundle is missing its executable." >&2
    return 1
  }

  rm -rf -- "$release_dir"
  mv "$extracted_dir/AXIOM" "$release_dir"
  ln -sfn "$release_dir" "$INSTALL_DIR/current"
  ln -sfn "$INSTALL_DIR/current/AXIOM" "$BIN_DIR/axiom"
  AXIOM_BIN="$BIN_DIR/axiom"
}

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
    command -v tar >/dev/null 2>&1 || { echo "Error: tar is required."; exit 1; }
    ARCH="$(uname -m)"
    if [ "$ARCH" = "x86_64" ]; then
      echo "Finding the latest AXIOM Linux release..."
      TAG="$(latest_release_tag)"
      [ -n "$TAG" ] || { echo "Error: could not determine an AXIOM release."; exit 1; }
      install_linux_bundle "$TAG"
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
"$AXIOM_BIN" --no-banner version
