#!/usr/bin/env bash
set -euo pipefail

OWNER="NetCore-Technologies"
REPO="AXIOM-AI"

CURRENT_VERSION="0.2.0-beta.4"
TARGET_VERSION="0.2.0-beta.5"
TARGET_TAG="v${TARGET_VERSION}"
PY_VERSION="0.2.0b5"

GPG_KEY="BA75335BF0BC7084"
GPG_NAME="Manit Arora"
GPG_EMAIL="manit6752025@gmail.com"

echo "============================================================"
echo " AXIOM RELEASE SECURITY FIX"
echo " ${CURRENT_VERSION} -> ${TARGET_VERSION}"
echo "============================================================"

# ------------------------------------------------------------
# Repository
# ------------------------------------------------------------
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"

if [[ -z "$ROOT" ]]; then
    echo "ERROR: not inside a Git repository."
    exit 1
fi

cd "$ROOT"

REMOTE="$(git remote get-url origin 2>/dev/null || true)"

if [[ "$REMOTE" != *"NetCore-Technologies/AXIOM-AI"* ]]; then
    echo "ERROR: wrong origin:"
    echo "$REMOTE"
    exit 1
fi

echo
echo "===== REPOSITORY ====="
pwd
git branch --show-current
git rev-parse --short HEAD

# ------------------------------------------------------------
# Protect existing tracked changes while syncing
# ------------------------------------------------------------
echo
echo "===== SYNC MAIN ====="

git fetch origin

git pull \
    --rebase \
    --autostash \
    origin main

echo "main synchronized."

# ------------------------------------------------------------
# GPG
# ------------------------------------------------------------
echo
echo "===== GPG ====="

git config --local user.name "$GPG_NAME"
git config --local user.email "$GPG_EMAIL"
git config --local user.signingkey "$GPG_KEY"
git config --local gpg.program gpg
git config --local commit.gpgSign true
git config --local tag.gpgSign true

export GPG_TTY="$(tty 2>/dev/null || true)"

if ! gpg --list-secret-keys "$GPG_KEY" >/dev/null 2>&1; then
    echo "ERROR: GPG private key $GPG_KEY is unavailable."
    exit 1
fi

echo "GPG signing key available."

# ------------------------------------------------------------
# Patch workflow action versions and pin ALL external actions
# ------------------------------------------------------------
echo
echo "===== PIN GITHUB ACTIONS ====="

python3 <<'PY'
from pathlib import Path
import re
import subprocess
import urllib.parse

WORKFLOW_DIR = Path(".github/workflows")

# Move these away from the older Node 20 action lines.
UPGRADES = {
    "actions/checkout": "v5.1.0",
    "actions/setup-node": "v6.5.0",
    "actions/upload-artifact": "v6.0.0",
}


def resolve_commit(repo: str, ref: str) -> str:
    """
    Resolve an action tag/branch to its actual commit SHA.
    Works without GitHub CLI authentication.
    """

    url = f"https://github.com/{repo}.git"

    # Annotated tag -> dereferenced commit.
    for remote_ref in (
        f"refs/tags/{ref}^{{}}",
        f"refs/tags/{ref}",
        f"refs/heads/{ref}",
    ):
        result = subprocess.run(
            ["git", "ls-remote", url, remote_ref],
            capture_output=True,
            text=True,
            check=False,
        )

        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and re.fullmatch(r"[0-9a-fA-F]{40}", parts[0]):
                return parts[0].lower()

    raise RuntimeError(
        f"Unable to resolve {repo}@{ref}"
    )


files = sorted(
    list(WORKFLOW_DIR.glob("*.yml")) +
    list(WORKFLOW_DIR.glob("*.yaml"))
)

if not files:
    raise SystemExit("No GitHub workflow files found.")

changed = []

# Matches:
#     uses: owner/repo@ref
#
# It deliberately skips:
#     ./local-action
#     docker://...
uses_re = re.compile(
    r"^(\s*-\s*uses:\s*)([^@\s]+)@([^\s#]+)(.*)$"
)

for path in files:
    original = path.read_text(encoding="utf-8").splitlines()

    output = []
    file_changed = False

    for line in original:
        match = uses_re.match(line)

        if not match:
            output.append(line)
            continue

        prefix, action, ref, _rest = match.groups()

        # Local / Docker actions are not GitHub repository actions.
        if action.startswith("./") or action.startswith("docker://"):
            output.append(line)
            continue

        # Upgrade the three affected actions.
        selected_ref = UPGRADES.get(action, ref)

        # Already pinned to an immutable full SHA.
        if re.fullmatch(r"[0-9a-fA-F]{40}", selected_ref):
            output.append(
                f"{prefix}{action}@{selected_ref} # pinned"
            )
            continue

        sha = resolve_commit(action, selected_ref)

        output.append(
            f"{prefix}{action}@{sha} # {selected_ref}"
        )

        if line != output[-1]:
            file_changed = True

        print(
            f"{path}: {action}@{selected_ref} -> {sha}"
        )

    new_text = "\n".join(output) + "\n"

    old_text = path.read_text(encoding="utf-8")

    if new_text != old_text:
        path.write_text(new_text, encoding="utf-8")
        changed.append(str(path))

print()
print("Workflow files changed:")

for item in changed:
    print(f"  {item}")
PY

# ------------------------------------------------------------
# Verify every external uses: is pinned
# ------------------------------------------------------------
echo
echo "===== VERIFY ACTION PINNING ====="

python3 <<'PY'
from pathlib import Path
import re

bad = []

pattern = re.compile(
    r"^\s*-\s*uses:\s*([^@\s]+)@([^\s#]+)"
)

for path in sorted(
    list(Path(".github/workflows").glob("*.yml")) +
    list(Path(".github/workflows").glob("*.yaml"))
):
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        match = pattern.match(line)

        if not match:
            continue

        action, ref = match.groups()

        if action.startswith("./"):
            continue

        if action.startswith("docker://"):
            continue

        if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
            bad.append(
                f"{path}:{number}: {action}@{ref}"
            )

if bad:
    print("UNPINNED ACTIONS FOUND:")
    for item in bad:
        print(item)
    raise SystemExit(1)

print("Every external GitHub Action uses a full 40-character commit SHA.")
PY

# ------------------------------------------------------------
# Show workflow changes
# ------------------------------------------------------------
echo
echo "===== WORKFLOW DIFF ====="

git diff -- .github/workflows

# ------------------------------------------------------------
# Python tests
# ------------------------------------------------------------
echo
echo "===== INSTALL AXIOM ====="

python3 -m pip install -e .
python3 -m pip install pytest

echo
echo "===== AXIOM VERSION ====="

axiom version

echo
echo "===== CLI TESTS ====="

axiom --help >/dev/null
axiom doctor
axiom info
axiom status

echo
echo "===== PYTEST ====="

python3 -m pytest -q

# ------------------------------------------------------------
# Frontend
# ------------------------------------------------------------
if [[ -f package.json ]]; then

    echo
    echo "===== FRONTEND ====="

    if npm run 2>/dev/null | grep -qE '^[[:space:]]+lint'; then
        npm run lint
    fi

    if npm run 2>/dev/null | grep -qE '^[[:space:]]+build'; then
        npm run build
    fi

fi

# ------------------------------------------------------------
# Version -> beta.5
# ------------------------------------------------------------
echo
echo "===== UPDATE VERSION ${TARGET_VERSION} ====="

python3 <<'PY'
from pathlib import Path
import re

DISPLAY = "0.2.0-beta.5"
PYTHON_VERSION = "0.2.0b5"

# pyproject.toml
p = Path("pyproject.toml")
s = p.read_text(encoding="utf-8")

match = re.search(
    r"(\[project\][\s\S]*?\nversion\s*=\s*[\"'])([^\"']+)([\"'])",
    s,
    re.MULTILINE,
)

if not match:
    raise SystemExit(
        "Could not locate [project] version in pyproject.toml"
    )

s = (
    s[:match.start(2)]
    + PYTHON_VERSION
    + s[match.end(2):]
)

p.write_text(s, encoding="utf-8")

# axiom/version.py
p = Path("axiom/version.py")

if p.exists():
    s = p.read_text(encoding="utf-8")

    updated, count = re.subn(
        r'(__version__\s*=\s*["\'])[^"\']+(["\'])',
        rf"\g<1>{DISPLAY}\g<2>",
        s,
        count=1,
    )

    if count:
        p.write_text(updated, encoding="utf-8")

print(f"Display version: {DISPLAY}")
print(f"Package version: {PYTHON_VERSION}")
PY

python3 -m pip install -e .

echo
axiom version

# ------------------------------------------------------------
# Release notes
# ------------------------------------------------------------
echo
echo "===== RELEASE NOTES ====="

mkdir -p docs/releases

cat > "docs/releases/${TARGET_TAG}.md" <<EOFMD
# AXIOM ${TARGET_TAG}

## CLI

Continues the AXIOM CLI expansion introduced in beta.4.

### Commands

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

## GitHub Actions security

All external GitHub Actions used by the repository are pinned
to immutable full-length commit SHAs.

The release workflow also uses current Node.js 24-compatible
action releases.

## Version

- AXIOM: ${TARGET_VERSION}
- Python package: 0.2.0b5

## Beta

AXIOM remains in active beta development.
EOFMD

# ------------------------------------------------------------
# Git validation
# ------------------------------------------------------------
echo
echo "===== GIT CHECK ====="

git diff --check

# ------------------------------------------------------------
# Stage ONLY release changes
# ------------------------------------------------------------
echo
echo "===== STAGE ====="

git add \
    .github/workflows \
    pyproject.toml \
    axiom/version.py \
    "docs/releases/${TARGET_TAG}.md"

git diff --cached --check

echo
echo "===== STAGED FILES ====="

git diff --cached --name-status

# ------------------------------------------------------------
# Commit
# ------------------------------------------------------------
echo
echo "===== SIGNED COMMIT ====="

GIT_AUTHOR_NAME="$GPG_NAME" \
GIT_AUTHOR_EMAIL="$GPG_EMAIL" \
GIT_COMMITTER_NAME="$GPG_NAME" \
GIT_COMMITTER_EMAIL="$GPG_EMAIL" \
git commit \
    -S"$GPG_KEY" \
    -m "fix: pin GitHub Actions for ${TARGET_TAG}"

echo
echo "===== VERIFY COMMIT ====="

git log -1 --show-signature --format=fuller

# ------------------------------------------------------------
# Push main
# ------------------------------------------------------------
echo
echo "===== PUSH MAIN ====="

git push origin main

# ------------------------------------------------------------
# Safety: never overwrite beta.5
# ------------------------------------------------------------
echo
echo "===== CHECK ${TARGET_TAG} ====="

if git ls-remote \
    --exit-code \
    --tags \
    origin \
    "refs/tags/${TARGET_TAG}" >/dev/null 2>&1; then

    echo
    echo "ERROR: ${TARGET_TAG} already exists remotely."
    echo "Refusing to overwrite it."
    exit 1
fi

# ------------------------------------------------------------
# Signed tag
# ------------------------------------------------------------
echo
echo "===== SIGN ${TARGET_TAG} ====="

GIT_COMMITTER_NAME="$GPG_NAME" \
GIT_COMMITTER_EMAIL="$GPG_EMAIL" \
git tag \
    -s \
    -u "$GPG_KEY" \
    "$TARGET_TAG" \
    -m "AXIOM ${TARGET_TAG} — release security and CLI update"

# ------------------------------------------------------------
# Verify tag
# ------------------------------------------------------------
echo
echo "===== VERIFY TAG ====="

git tag -v "$TARGET_TAG"

# ------------------------------------------------------------
# Push tag
# ------------------------------------------------------------
echo
echo "===== PUSH TAG ====="

git push origin "$TARGET_TAG"

# ------------------------------------------------------------
# Final
# ------------------------------------------------------------
echo
echo "============================================================"
echo " AXIOM ${TARGET_TAG} RELEASE TRIGGERED"
echo "============================================================"

echo
echo "Release:"
echo "https://github.com/${OWNER}/${REPO}/releases/tag/${TARGET_TAG}"

echo
echo "Actions:"
echo "https://github.com/${OWNER}/${REPO}/actions"

if command -v gh >/dev/null 2>&1; then
    echo
    echo "===== RECENT RUNS ====="

    gh run list \
        --repo "${OWNER}/${REPO}" \
        --limit 10 || true
fi
