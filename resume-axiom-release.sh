#!/usr/bin/env bash
set -euo pipefail

VERSION="0.2.0-beta.4"
TAG="v${VERSION}"
GPG_KEY="BA75335BF0BC7084"
GPG_NAME="Manit Arora"
GPG_EMAIL="manit6752025@gmail.com"

echo "============================================================"
echo " AXIOM ${TAG} RELEASE BUILDER"
echo "============================================================"

# ------------------------------------------------------------
# Locate repository
# ------------------------------------------------------------
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"

if [[ -z "$ROOT" ]]; then
    echo "ERROR: not inside a Git repository."
    exit 1
fi

cd "$ROOT"

REMOTE="$(git remote get-url origin 2>/dev/null || true)"

if [[ "$REMOTE" != *"NetCore-Technologies/AXIOM-AI"* ]]; then
    echo "ERROR: origin is not NetCore-Technologies/AXIOM-AI"
    echo "Origin: $REMOTE"
    exit 1
fi

echo
echo "===== REPOSITORY ====="
echo "Root: $ROOT"
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"

# ------------------------------------------------------------
# Preserve ALL current work before sync
# ------------------------------------------------------------
echo
echo "===== PRESERVE CURRENT WORK ====="

STASH_CREATED=0

if ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
    echo "Changes detected."
    echo "Creating temporary stash including untracked files..."

    git stash push -u -m "AXIOM beta.4 release temporary stash"

    STASH_CREATED=1

    echo "Temporary stash created."
else
    echo "Working tree already clean."
fi

# ------------------------------------------------------------
# Sync origin/main
# ------------------------------------------------------------
echo
echo "===== SYNC MAIN ====="

git fetch origin

git rebase origin/main

echo "Main synchronized."

# ------------------------------------------------------------
# Restore work
# ------------------------------------------------------------
if [[ "$STASH_CREATED" -eq 1 ]]; then
    echo
    echo "===== RESTORE CURRENT WORK ====="

    if ! git stash pop; then
        echo
        echo "ERROR: stash restoration produced conflicts."
        echo "Your work remains in the Git stash."
        echo
        git stash list | head -5
        exit 1
    fi

    echo "Current work restored."
fi

# ------------------------------------------------------------
# GPG configuration
# ------------------------------------------------------------
echo
echo "===== GPG SIGNING ====="

git config --local user.name "$GPG_NAME"
git config --local user.email "$GPG_EMAIL"
git config --local user.signingkey "$GPG_KEY"
git config --local gpg.program gpg
git config --local commit.gpgSign true
git config --local tag.gpgSign true

export GPG_TTY="$(tty 2>/dev/null || true)"

gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1 || true

if ! gpg --list-secret-keys "$GPG_KEY" >/dev/null 2>&1; then
    echo "ERROR: GPG private key $GPG_KEY is not available."
    exit 1
fi

echo "GPG key available."

# ------------------------------------------------------------
# Install AXIOM
# ------------------------------------------------------------
echo
echo "===== INSTALL AXIOM ====="

python3 -m pip install -e .

echo
echo "AXIOM command:"
command -v axiom

echo
echo "Version:"
axiom version

# ------------------------------------------------------------
# Ensure pytest
# ------------------------------------------------------------
echo
echo "===== INSTALL TEST TOOLS ====="

python3 -m pip install pytest

python3 -m pytest --version

# ------------------------------------------------------------
# Verify CLI files exist
# ------------------------------------------------------------
echo
echo "===== VERIFY CLI IMPLEMENTATION ====="

test -f axiom/cli/main.py
test -f axiom/cli/extended.py

echo "main.py: OK"
echo "extended.py: OK"

# ------------------------------------------------------------
# CLI checks
# ------------------------------------------------------------
echo
echo "===== CLI HELP ====="

axiom --help

echo
echo "===== ROOT COMMANDS ====="

axiom version
axiom doctor
axiom info
axiom status

echo
echo "===== MODEL COMMANDS ====="

axiom model --help

echo
echo "===== DATASET COMMANDS ====="

axiom dataset --help

echo
echo "===== PROJECT COMMANDS ====="

axiom project --help

echo
echo "===== CONFIG COMMANDS ====="

axiom config --help

# ------------------------------------------------------------
# Dataset integration test
# ------------------------------------------------------------
echo
echo "===== DATASET INTEGRATION TEST ====="

TEST_ROOT="$(mktemp -d)"

cleanup() {
    rm -rf "$TEST_ROOT"
}

trap cleanup EXIT

cat > "$TEST_ROOT/train.jsonl" <<'JSONL'
{"instruction":"hello","output":"world"}
{"instruction":"hello","output":"world"}
{"instruction":"test","output":"success"}
JSONL

axiom dataset validate "$TEST_ROOT/train.jsonl"
axiom dataset stats "$TEST_ROOT/train.jsonl"

# ------------------------------------------------------------
# Project integration test
# ------------------------------------------------------------
echo
echo "===== PROJECT INTEGRATION TEST ====="

mkdir -p \
    "$TEST_ROOT/project/data" \
    "$TEST_ROOT/project/models" \
    "$TEST_ROOT/project/experiments" \
    "$TEST_ROOT/project/evaluations" \
    "$TEST_ROOT/project/outputs"

cat > "$TEST_ROOT/project/axiom.yaml" <<'YAML'
project:
  name: axiom-release-test
YAML

cat > "$TEST_ROOT/project/README.md" <<'EOFMD'
# AXIOM Release Test
EOFMD

(
    cd "$TEST_ROOT/project"

    axiom project validate
    axiom project info
    axiom config validate
    axiom config show
)

echo
echo "CLI integration tests passed."

# ------------------------------------------------------------
# Python tests
# ------------------------------------------------------------
echo
echo "===== PYTEST ====="

python3 -m pytest -q

echo
echo "PYTEST PASSED."

# ------------------------------------------------------------
# Frontend validation
# ------------------------------------------------------------
if [[ -f package.json ]]; then

    echo
    echo "===== FRONTEND ====="

    if npm run 2>/dev/null | grep -qE '^[[:space:]]+lint'; then
        echo "Running npm lint..."
        npm run lint
    else
        echo "No npm lint script."
    fi

    if npm run 2>/dev/null | grep -qE '^[[:space:]]+build'; then
        echo "Running npm build..."
        npm run build
    else
        echo "No npm build script."
    fi

else
    echo
    echo "No package.json — frontend checks skipped."
fi

# ------------------------------------------------------------
# Version update
# ------------------------------------------------------------
echo
echo "===== UPDATE VERSION ====="

python3 <<'PY'
from pathlib import Path
import re

display_version = "0.2.0-beta.4"
package_version = "0.2.0b4"

# pyproject.toml
p = Path("pyproject.toml")
s = p.read_text(encoding="utf-8")

project_match = re.search(
    r'(\[project\][\s\S]*?\nversion\s*=\s*["\'])([^"\']+)(["\'])',
    s,
    re.MULTILINE,
)

if not project_match:
    raise SystemExit("ERROR: [project] version not found in pyproject.toml")

s = (
    s[:project_match.start(2)]
    + package_version
    + s[project_match.end(2):]
)

p.write_text(s, encoding="utf-8")

# axiom/version.py
p = Path("axiom/version.py")

if p.exists():
    s = p.read_text(encoding="utf-8")

    updated, count = re.subn(
        r'(__version__\s*=\s*["\'])[^"\']+(["\'])',
        rf'\g<1>{display_version}\g<2>',
        s,
        count=1,
    )

    if count:
        p.write_text(updated, encoding="utf-8")

print("AXIOM display version:", display_version)
print("Python package version:", package_version)
PY

# Reinstall after version change.
python3 -m pip install -e .

echo
echo "===== VERSION VERIFICATION ====="

axiom version

# ------------------------------------------------------------
# Release notes
# ------------------------------------------------------------
echo
echo "===== RELEASE NOTES ====="

mkdir -p docs/releases

cat > "docs/releases/${TAG}.md" <<EOFMD
# AXIOM ${TAG}

## CLI expansion

AXIOM ${TAG} expands the command-line engineering workflow while
preserving the existing AXIOM CLI.

### New commands

\`\`\`text
axiom doctor
axiom info
axiom status

axiom model inspect <path>
axiom model search <query>

axiom dataset validate <path>
axiom dataset stats <path>

axiom project info
axiom project validate

axiom config show
axiom config validate
\`\`\`

### Existing workflows

Existing model, dataset, training, Hugging Face, SuperCompress,
integration, and MCP workflows remain supported.

## Version

Display version: ${VERSION}

Python package version: 0.2.0b4

## Validation

This release is validated with the AXIOM Python test suite,
CLI integration checks, and available frontend lint/build checks.

## Beta

AXIOM ${VERSION} remains a beta release under active development.
EOFMD

echo "Release notes created."

# ------------------------------------------------------------
# Final diff validation
# ------------------------------------------------------------
echo
echo "===== GIT DIFF CHECK ====="

git diff --check

# ------------------------------------------------------------
# Stage ONLY intended files
# ------------------------------------------------------------
echo
echo "===== STAGE RELEASE FILES ====="

git add \
    axiom/cli/main.py \
    axiom/cli/extended.py \
    axiom/version.py \
    pyproject.toml \
    tests/test_cli_extended.py \
    "docs/releases/${TAG}.md"

git diff --cached --check

echo
echo "===== STAGED FILES ====="

git diff --cached --name-status

# ------------------------------------------------------------
# Make sure we actually have changes
# ------------------------------------------------------------
if git diff --cached --quiet; then
    echo
    echo "ERROR: nothing staged for the release."
    exit 1
fi

# ------------------------------------------------------------
# Signed commit
# ------------------------------------------------------------
echo
echo "===== CREATE SIGNED COMMIT ====="

GIT_AUTHOR_NAME="$GPG_NAME" \
GIT_AUTHOR_EMAIL="$GPG_EMAIL" \
GIT_COMMITTER_NAME="$GPG_NAME" \
GIT_COMMITTER_EMAIL="$GPG_EMAIL" \
git commit \
    -S"$GPG_KEY" \
    -m "feat: expand AXIOM CLI for ${TAG}"

# ------------------------------------------------------------
# Verify signed commit
# ------------------------------------------------------------
echo
echo "===== VERIFY SIGNED COMMIT ====="

git log \
    -1 \
    --show-signature \
    --format=fuller

# ------------------------------------------------------------
# Push main
# ------------------------------------------------------------
echo
echo "===== PUSH MAIN ====="

git push origin main

echo "main pushed successfully."

# ------------------------------------------------------------
# Check if tag already exists
# ------------------------------------------------------------
echo
echo "===== CHECK RELEASE TAG ====="

if git ls-remote \
    --exit-code \
    --tags \
    origin \
    "refs/tags/${TAG}" >/dev/null 2>&1; then

    echo
    echo "${TAG} already exists on origin."
    echo "No tag overwrite will be attempted."
    echo
    echo "Release:"
    echo "https://github.com/NetCore-Technologies/AXIOM-AI/releases/tag/${TAG}"

    exit 0
fi

# ------------------------------------------------------------
# Create signed tag
# ------------------------------------------------------------
echo
echo "===== CREATE SIGNED TAG ====="

GIT_COMMITTER_NAME="$GPG_NAME" \
GIT_COMMITTER_EMAIL="$GPG_EMAIL" \
git tag \
    -s \
    -u "$GPG_KEY" \
    "$TAG" \
    -m "AXIOM ${TAG} — CLI expansion and engineering update"

# ------------------------------------------------------------
# Verify signed tag
# ------------------------------------------------------------
echo
echo "===== VERIFY SIGNED TAG ====="

git tag -v "$TAG"

# ------------------------------------------------------------
# Push tag
# ------------------------------------------------------------
echo
echo "===== PUSH TAG ====="

git push origin "$TAG"

# ------------------------------------------------------------
# Final state
# ------------------------------------------------------------
echo
echo "===== FINAL STATUS ====="

git status --short --branch

echo
echo "============================================================"
echo " AXIOM ${TAG} RELEASE TRIGGERED"
echo "============================================================"

echo
echo "Release:"
echo "https://github.com/NetCore-Technologies/AXIOM-AI/releases/tag/${TAG}"

echo
echo "Actions:"
echo "https://github.com/NetCore-Technologies/AXIOM-AI/actions"

# ------------------------------------------------------------
# Show recent workflow runs if gh exists
# ------------------------------------------------------------
if command -v gh >/dev/null 2>&1; then
    echo
    echo "===== RECENT GITHUB ACTIONS ====="

    gh run list \
        --repo NetCore-Technologies/AXIOM-AI \
        --limit 5 || true
fi
