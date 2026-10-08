#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "======================================================================"
echo " AXIOM REPO CLEANUP"
echo " Remove backup files + user-made root .sh files"
echo "======================================================================"

# Root-level helper/release scripts that were created during the repair cycle.
# Do NOT touch scripts/ project tooling or .github workflows.
ROOT_SCRIPTS=(
  axiom_beta5_feature_patch.sh
  cli-release.sh
  does.sh
  fix-actions-and-release.sh
  h.sh
  l.sh
  remake-beta4.sh
  resume-axiom-release.sh
  somthing.sh
  help.sh
  repair.sh
  axiom_beta5_stabilize_release.sh
  axiom_beta5_all_in_one_release.sh
  axiom_beta5_repair_and_release.sh
  axiom_beta5_full_fix_release.sh
  axiom_beta5_final_release_fix.sh
  axiom_beta5_final_one_shot.sh
  axiom_beta5_full_app_fix_release.sh
  axiom_beta5_all_in_one_release.sh
  axiom_beta5_gui_patch.sh
  axiom_beta5_gui_fix.sh
)

# Backup/temp source files visible in the repository.
BACKUP_GLOBS=(
  'src/App.tsx.before-*'
  'src/App.tsx.*backup*'
  'src/App.tsx.beta5-*'
  'src/styles.css.backup'
  'src/styles.css.before-*'
  'src/styles.css.bad-import*'
  'src/styles.css.beta5-*'
  'src/styles.css.broken-theme'
  'src/styles.css.current-broken'
  'tests/test_backend.py.before-*'
  'tests/test_backend.py.corrupted'
)

# Also remove hidden backup directories created inside the repository.
find . -maxdepth 1 -type d \( -name '.axiom-beta5-*' -o -name '.beta5-*' \) -prune -exec rm -rf {} +

for f in "${ROOT_SCRIPTS[@]}"; do
  rm -f -- "$f"
done

for pattern in "${BACKUP_GLOBS[@]}"; do
  # shellcheck disable=SC2086
  rm -f -- $pattern
 done

# Remove common untracked scratch artifacts if they are still only local.
# These names came from the repair/build cycle and are not project source.
rm -f -- axiom-ui@0.1.0 eslint tsc

# Never stage anything outside the intended cleanup unless it is already tracked.
# Show exactly what will be removed.
echo
echo "== CLEANUP STATUS =="
git status --short

echo
echo "== REMAINING ROOT SHELL SCRIPTS =="
find . -maxdepth 1 -type f -name '*.sh' -printf '%f\n' | sort || true

echo
echo "== COMMITTING CLEANUP =="
git add -A

if git diff --cached --quiet; then
  echo "Nothing to commit."
  exit 0
fi

git diff --cached --stat

git commit -S -m "chore: remove release repair artifacts"
git push origin main

echo
echo "======================================================================"
echo " CLEANUP PUSHED"
echo "======================================================================"
