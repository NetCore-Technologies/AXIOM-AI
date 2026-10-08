#!/usr/bin/env bash
set -euo pipefail

OWNER="NetCore-Technologies"
REPO="AXIOM-AI"

TAGS=(
  "v0.2.0-beta.4"
  "v0.2.0-beta.5"
)

TARGET="v0.2.0-beta.4"

GPG_KEY="BA75335BF0BC7084"
GPG_NAME="Manit Arora"
GPG_EMAIL="manit6752025@gmail.com"

echo "============================================================"
echo " AXIOM RELEASE RESET"
echo " Remove beta.4 + beta.5"
echo " Recreate beta.4"
echo "============================================================"

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

REMOTE="$(git remote get-url origin)"

if [[ "$REMOTE" != *"NetCore-Technologies/AXIOM-AI"* ]]; then
  echo "ERROR: wrong Git remote:"
  echo "$REMOTE"
  exit 1
fi

echo
echo "===== CURRENT HEAD ====="
git log -1 --oneline

echo
echo "===== FETCH ====="
git fetch origin

# ------------------------------------------------------------
# Delete GitHub releases
# ------------------------------------------------------------
echo
echo "===== DELETE OLD RELEASES ====="

for TAG in "${TAGS[@]}"; do
  if gh release view "$TAG" --repo "$OWNER/$REPO" >/dev/null 2>&1; then
    echo "Deleting release $TAG"
    gh release delete "$TAG" \
      --repo "$OWNER/$REPO" \
      --yes
  else
    echo "Release $TAG not found"
  fi
done

# ------------------------------------------------------------
# Delete remote tags
# ------------------------------------------------------------
echo
echo "===== DELETE REMOTE TAGS ====="

for TAG in "${TAGS[@]}"; do
  if git ls-remote \
      --exit-code \
      --tags \
      origin \
      "refs/tags/$TAG" >/dev/null 2>&1; then

    echo "Deleting remote tag $TAG"
    git push origin --delete "$TAG"
  else
    echo "Remote tag $TAG not found"
  fi
done

# ------------------------------------------------------------
# Delete local tags
# ------------------------------------------------------------
echo
echo "===== DELETE LOCAL TAGS ====="

for TAG in "${TAGS[@]}"; do
  git tag -d "$TAG" 2>/dev/null || true
done

# ------------------------------------------------------------
# Make sure beta.4 does not exist anywhere
# ------------------------------------------------------------
echo
echo "===== VERIFY CLEAN TAG STATE ====="

if git ls-remote \
    --exit-code \
    --tags \
    origin \
    "refs/tags/$TARGET" >/dev/null 2>&1; then
  echo "ERROR: $TARGET still exists remotely."
  exit 1
fi

if git tag --list "$TARGET" | grep -qx "$TARGET"; then
  echo "ERROR: $TARGET still exists locally."
  exit 1
fi

echo "Old beta.4/beta.5 tags removed."

# ------------------------------------------------------------
# GPG configuration
# ------------------------------------------------------------
echo
echo "===== GPG ====="

git config --local user.name "$GPG_NAME"
git config --local user.email "$GPG_EMAIL"
git config --local user.signingkey "$GPG_KEY"
git config --local gpg.program gpg

if ! gpg --list-secret-keys "$GPG_KEY" >/dev/null 2>&1; then
  echo "ERROR: GPG key $GPG_KEY is not available."
  exit 1
fi

# ------------------------------------------------------------
# Create fresh signed beta.4 tag on current HEAD
# ------------------------------------------------------------
echo
echo "===== CREATE FRESH $TARGET ====="

GIT_COMMITTER_NAME="$GPG_NAME" \
GIT_COMMITTER_EMAIL="$GPG_EMAIL" \
git tag -s \
  -u "$GPG_KEY" \
  "$TARGET" \
  -m "AXIOM $TARGET"

# ------------------------------------------------------------
# Verify
# ------------------------------------------------------------
echo
echo "===== VERIFY TAG ====="

git tag -v "$TARGET"

echo
echo "Tagged commit:"
git rev-list -n 1 "$TARGET"

echo
echo "Current HEAD:"
git rev-parse HEAD

# ------------------------------------------------------------
# Push
# ------------------------------------------------------------
echo
echo "===== PUSH TAG ====="

git push origin "$TARGET"

# ------------------------------------------------------------
# Create GitHub release from fresh tag
# ------------------------------------------------------------
echo
echo "===== CREATE GITHUB RELEASE ====="

gh release create "$TARGET" \
  --repo "$OWNER/$REPO" \
  --title "AXIOM $TARGET" \
  --notes-file "docs/releases/$TARGET.md" \
  --prerelease

echo
echo "============================================================"
echo " BOOM — FRESH $TARGET CREATED"
echo "============================================================"

echo
echo "Release:"
echo "https://github.com/$OWNER/$REPO/releases/tag/$TARGET"
echo
echo "Actions:"
echo "https://github.com/$OWNER/$REPO/actions"
