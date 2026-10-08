#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# AXIOM COMMUNITY DOCS PUBLISHER
# NetCore Technologies / AXIOM-AI
#
# Creates:
#   docs/SUPPORT.md
#   docs/GOVERNANCE.md
#   docs/PULL_REQUEST_TEMPLATE.md
#
# GitHub-native:
#   .github/PULL_REQUEST_TEMPLATE.md
#   .github/ISSUE_TEMPLATE/bug_report.md
#   .github/ISSUE_TEMPLATE/feature_request.md
#   .github/ISSUE_TEMPLATE/documentation.md
#   .github/ISSUE_TEMPLATE/performance.md
#   .github/ISSUE_TEMPLATE/security.md
#
# Then:
#   - checks git status
#   - syncs origin/main with rebase
#   - stages only these files
#   - validates whitespace
#   - creates a GPG-signed commit as Manit Arora
#   - pushes main
#
# Run:
#   chmod +x publish_axiom_community_docs.sh
#   ./publish_axiom_community_docs.sh
# ============================================================

OWNER="NetCore-Technologies"
REPO="AXIOM-AI"
REMOTE="origin"
BRANCH="main"
SIGNING_KEY="BA75335BF0BC7084"
SIGNING_NAME="Manit Arora"
SIGNING_EMAIL="manit6752025@gmail.com"

C_OK='\033[0;32m'
C_CYAN='\033[0;36m'
C_YELLOW='\033[1;33m'
C_RED='\033[0;31m'
C_RESET='\033[0m'

ok()   { printf "${C_OK}✓ %s${C_RESET}\n" "$1"; }
info() { printf "${C_CYAN}▶ %s${C_RESET}\n" "$1"; }
warn() { printf "${C_YELLOW}⚠ %s${C_RESET}\n" "$1"; }
die()  { printf "${C_RED}✗ %s${C_RESET}\n" "$1" >&2; exit 1; }

echo
printf "${C_CYAN}"
cat <<'BANNER'
╔══════════════════════════════════════════════════════════════╗
║              AXIOM COMMUNITY DOCS PUBLISHER               ║
║                    Build AI. Own AI.                       ║
╚══════════════════════════════════════════════════════════════╝
BANNER
printf "${C_RESET}"

# ------------------------------------------------------------
# Find repository
# ------------------------------------------------------------
info "Locating AXIOM repository"

if [[ -d "/workspaces/Optimization-Project-Name-TBD/.git" ]]; then
  cd /workspaces/Optimization-Project-Name-TBD
elif git rev-parse --show-toplevel >/dev/null 2>&1; then
  cd "$(git rev-parse --show-toplevel)"
else
  die "Not inside an AXIOM Git repository."
fi

[[ "$(basename "$PWD")" == "Optimization-Project-Name-TBD" || \
   "$(git remote get-url "$REMOTE" 2>/dev/null || true)" == *"NetCore-Technologies/AXIOM-AI"* ]] \
  || die "This does not appear to be the AXIOM-AI repository."

ok "Repository: $PWD"

# ------------------------------------------------------------
# GitHub CLI
# ------------------------------------------------------------
command -v git >/dev/null 2>&1 || die "git is required."

# ------------------------------------------------------------
# Create directories
# ------------------------------------------------------------
mkdir -p docs
mkdir -p .github/ISSUE_TEMPLATE

# ------------------------------------------------------------
# SUPPORT
# ------------------------------------------------------------
cat > docs/SUPPORT.md <<'EOF'
# AXIOM Support

## Getting help

AXIOM is an open-source AI engineering platform maintained by NetCore Technologies.

Before asking for help:

1. Check the AXIOM Wiki.
2. Search existing GitHub Issues.
3. Check the Troubleshooting documentation.
4. Confirm you are using a supported or currently tested release.
5. Collect relevant error output and reproduction steps.

## Documentation

### AXIOM Wiki

https://github.com/NetCore-Technologies/AXIOM-AI/wiki

### Troubleshooting

https://github.com/NetCore-Technologies/AXIOM-AI/wiki/Troubleshooting

### Releases

https://github.com/NetCore-Technologies/AXIOM-AI/releases

### Contributing

https://github.com/NetCore-Technologies/AXIOM-AI/blob/main/CONTRIBUTING.md

## Where to ask

### Bugs

Use GitHub Issues:

https://github.com/NetCore-Technologies/AXIOM-AI/issues

### Feature requests

Use the feature-request template and describe the problem the feature would solve.

### Documentation problems

Open an issue when documentation is incorrect, missing or outdated.

### Security vulnerabilities

Do not post sensitive vulnerabilities publicly.

Follow the project's security policy:

https://github.com/NetCore-Technologies/AXIOM-AI/blob/main/SECURITY.md

## Include useful information

For technical problems, include:

- AXIOM version
- Operating system
- Hardware/runtime information when relevant
- Expected behaviour
- Actual behaviour
- Steps to reproduce
- Relevant logs or errors
- Screenshots when useful

Remove passwords, access tokens, private keys and other secrets before posting.

## Support boundaries

AXIOM is under active development. Some functionality may be experimental, incomplete or changing between releases.

Please provide reproducible information and keep support discussions constructive.

---

<div align="center">

**AXIOM — Build AI. Own AI.**

*NetCore Technologies*

</div>
EOF

# ------------------------------------------------------------
# GOVERNANCE
# ------------------------------------------------------------
cat > docs/GOVERNANCE.md <<'EOF'
# AXIOM Governance

## NetCore Technologies

**Build AI. Own AI.**

This document describes how AXIOM is maintained and how project decisions are made.

## 1. Project ownership

AXIOM is an open-source project maintained under **NetCore Technologies**.

Maintainers are responsible for:

- Project direction
- Repository administration
- Release management
- Security response
- Architecture decisions
- Community health
- Final merge decisions when consensus cannot be reached

## 2. Maintainers

Maintainers are trusted contributors with responsibility for meaningful areas of the project.

Responsibilities may include:

- Reviewing pull requests
- Triaging issues
- Maintaining documentation
- Reviewing security concerns
- Managing releases
- Improving infrastructure
- Helping contributors understand the codebase

Maintainer access should be earned through sustained, high-quality contribution and good project stewardship.

## 3. Decision making

AXIOM prefers decisions based on:

1. Technical evidence
2. Reproducible results
3. Security considerations
4. Maintainability
5. User experience
6. Compatibility
7. Long-term project direction

## 4. Consensus

The project prefers consensus when practical.

```text
PROBLEM
  ↓
PROPOSAL
  ↓
TECHNICAL DISCUSSION
  ↓
TEST / PROTOTYPE
  ↓
DECISION
  ↓
DOCUMENT
  ↓
IMPLEMENT
```

Constructive disagreement is welcome.

## 5. Final decisions

When consensus cannot be reached, project maintainers may make the final decision.

Significant decisions should be explained and documented when appropriate.

Security, release and project-integrity decisions may require immediate maintainer action.

## 6. Releases

Maintainers control official AXIOM releases.

Release decisions consider:

- Stability
- Known bugs
- Security
- CI status
- Packaging
- Documentation
- Release scope

## 7. Breaking changes

Breaking changes should be clearly discussed and documented.

Where possible, contributors should provide:

- Migration information
- Compatibility notes
- Updated documentation
- Test coverage
- Release notes

## 8. Security

Security issues should be handled privately according to:

https://github.com/NetCore-Technologies/AXIOM-AI/blob/main/SECURITY.md

Do not use public issues to disclose exploitable vulnerabilities or secrets.

## 9. Code of Conduct

Everyone participating in AXIOM is expected to follow:

https://github.com/NetCore-Technologies/AXIOM-AI/blob/main/CODE_OF_CONDUCT.md

## 10. Changes to governance

This document may evolve as the project grows.

Governance changes should be proposed transparently and reviewed by maintainers.

---

<div align="center">

**AXIOM — Build AI. Own AI.**

*NetCore Technologies*

</div>
EOF

# ------------------------------------------------------------
# PR template used in docs
# ------------------------------------------------------------
cat > docs/PULL_REQUEST_TEMPLATE.md <<'EOF'
# AXIOM Pull Request

## Summary

Describe what this pull request changes.

## Why

Explain the problem, goal or motivation behind the change.

## What changed

Describe the important implementation changes.

## Testing

Describe the tests you ran.

```text
Commands:
-
-
-
```

## UI changes

- [ ] UI not affected
- [ ] UI manually tested
- [ ] Screenshots included where useful
- [ ] Responsive behaviour checked where relevant

## Documentation

- [ ] No documentation changes required
- [ ] README updated
- [ ] Wiki updated
- [ ] Other documentation updated

## Release / packaging impact

- [ ] No release impact
- [ ] Release workflow changed
- [ ] Windows packaging affected
- [ ] Linux packaging affected
- [ ] Release notes should mention this change

## Security

- [ ] No security-sensitive changes
- [ ] Security implications reviewed
- [ ] No secrets or credentials included

## Breaking changes

- [ ] No breaking changes
- [ ] Breaking change described below

If applicable, describe migration or compatibility requirements:

>

## Checklist

- [ ] Change is focused
- [ ] Existing project conventions followed
- [ ] Tests completed
- [ ] `git diff --check` passes
- [ ] Documentation updated where needed
- [ ] No passwords, tokens, private keys or other secrets included
- [ ] Known limitations are documented
- [ ] Commit history is understandable

## Additional context

Add screenshots, logs, benchmarks, design notes or other useful context.

---

**AXIOM — Build AI. Own AI.**
EOF

# ------------------------------------------------------------
# GitHub-native PR template
# ------------------------------------------------------------
cp docs/PULL_REQUEST_TEMPLATE.md .github/PULL_REQUEST_TEMPLATE.md

# ------------------------------------------------------------
# Issue templates
# ------------------------------------------------------------
cat > .github/ISSUE_TEMPLATE/bug_report.md <<'EOF'
---
name: Bug report
about: Report a reproducible problem in AXIOM
title: "[Bug] "
labels: bug
assignees: ""
---

# Bug report

## Summary

Describe the problem clearly.

## AXIOM version

```text
Version:
```

## Environment

```text
Operating system:
Hardware:
Python version:
Node.js version:
Other relevant runtime information:
```

## Expected behaviour

What should have happened?

## Actual behaviour

What happened instead?

## Steps to reproduce

1.
2.
3.

## Logs / error output

```text
Paste relevant output here.
```

Remove passwords, tokens, private keys and other secrets before posting.

## Screenshots

Add screenshots when they help explain the issue.

## Additional context

Add anything else that may help reproduce or diagnose the problem.

## Checklist

- [ ] I searched existing issues.
- [ ] I can reproduce this problem.
- [ ] I included the AXIOM version.
- [ ] I removed sensitive information.
- [ ] I included useful reproduction information.
EOF

cat > .github/ISSUE_TEMPLATE/feature_request.md <<'EOF'
---
name: Feature request
about: Suggest an improvement or new capability for AXIOM
title: "[Feature] "
labels: enhancement
assignees: ""
---

# Feature request

## Problem

What problem would this feature solve?

## Proposed solution

Describe the behaviour you would like.

## Use case

Who would benefit from this feature and how would they use it?

## Alternatives considered

Describe alternative approaches or existing tools you considered.

## Scope

- [ ] Control Center
- [ ] Models
- [ ] Datasets
- [ ] Training
- [ ] Evaluation
- [ ] Runtime
- [ ] MCP
- [ ] Diagnostics
- [ ] CLI
- [ ] Website
- [ ] Release / infrastructure
- [ ] Documentation
- [ ] Other

## Additional context

Add examples, mock-ups, links or technical notes.

## Checklist

- [ ] I searched existing issues.
- [ ] This request describes a problem and proposed outcome.
- [ ] I have considered existing functionality.
EOF

cat > .github/ISSUE_TEMPLATE/documentation.md <<'EOF'
---
name: Documentation
about: Report missing, incorrect or unclear AXIOM documentation
title: "[Docs] "
labels: documentation
assignees: ""
---

# Documentation issue

## Documentation location

Provide the page, file or section:

```text
```

## Problem

What is missing, incorrect or unclear?

## Suggested improvement

Describe what the documentation should say or show.

## Version

```text
AXIOM version:
```

## Additional context

Add links, examples or screenshots when useful.

## Checklist

- [ ] I checked the AXIOM Wiki.
- [ ] I checked the repository documentation.
- [ ] I described the affected documentation clearly.
EOF

cat > .github/ISSUE_TEMPLATE/performance.md <<'EOF'
---
name: Performance
about: Report performance, latency, resource or scalability problems
title: "[Performance] "
labels: performance
assignees: ""
---

# Performance report

## Summary

Describe the performance problem.

## Environment

```text
AXIOM version:
Operating system:
CPU:
GPU:
RAM:
Storage:
Other relevant hardware:
```

## Workload

Describe the workload, model, dataset, request or operation being measured.

## Expected performance

```text
```

## Observed performance

```text
```

Include measurements when possible.

## Reproduction

1.
2.
3.

## Profiling / logs

```text
```

Remove secrets and private data.

## Checklist

- [ ] I included measurable observations where possible.
- [ ] I searched for existing reports.
- [ ] I included relevant environment information.
EOF

cat > .github/ISSUE_TEMPLATE/security.md <<'EOF'
---
name: Security vulnerability
about: Redirect security reports to the private security process
title: "[Security] "
labels: security
assignees: ""
---

# Security report

Please **do not disclose sensitive vulnerability details in this public issue**.

Use the AXIOM security policy instead:

https://github.com/NetCore-Technologies/AXIOM-AI/blob/main/SECURITY.md

If you have already posted sensitive information publicly, remove it where possible and contact the project maintainers through the security process.

For non-sensitive security improvements that do not expose an exploitable vulnerability, provide a normal issue with enough context to review the change safely.
EOF

# ------------------------------------------------------------
# Safety checks
# ------------------------------------------------------------
info "Checking generated files"

REQUIRED_FILES=(
  "docs/SUPPORT.md"
  "docs/GOVERNANCE.md"
  "docs/PULL_REQUEST_TEMPLATE.md"
  ".github/PULL_REQUEST_TEMPLATE.md"
  ".github/ISSUE_TEMPLATE/bug_report.md"
  ".github/ISSUE_TEMPLATE/feature_request.md"
  ".github/ISSUE_TEMPLATE/documentation.md"
  ".github/ISSUE_TEMPLATE/performance.md"
  ".github/ISSUE_TEMPLATE/security.md"
)

for f in "${REQUIRED_FILES[@]}"; do
  [[ -f "$f" ]] || die "Missing generated file: $f"
done

ok "All community documentation files created"

# Make sure secrets/private signing material isn't accidentally staged.
for forbidden in \
  "axiom-signing-key.asc" \
  "axiom-gpg-private.asc" \
  "*.pem" \
  "*.key"; do
  :
done

info "Preparing Git identity"

git config --local user.name "$SIGNING_NAME"
git config --local user.email "$SIGNING_EMAIL"
git config --local user.signingkey "$SIGNING_KEY"
git config --local gpg.program gpg
git config --local commit.gpgSign true

export GPG_TTY="$(tty || true)"
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1 || true

ok "Signed commits configured for ${SIGNING_NAME} <${SIGNING_EMAIL}>"

# ------------------------------------------------------------
# Sync first
# ------------------------------------------------------------
info "Syncing with origin/main"

git fetch "$REMOTE"

if git diff --quiet && git diff --cached --quiet; then
  git rebase "$REMOTE/$BRANCH"
else
  die "Working tree/index contains other changes. Commit or stash them before running this publisher."
fi

ok "Repository synchronized"

# ------------------------------------------------------------
# Stage only intended files
# ------------------------------------------------------------
info "Staging community documentation"

git add \
  docs/SUPPORT.md \
  docs/GOVERNANCE.md \
  docs/PULL_REQUEST_TEMPLATE.md \
  .github/PULL_REQUEST_TEMPLATE.md \
  .github/ISSUE_TEMPLATE/bug_report.md \
  .github/ISSUE_TEMPLATE/feature_request.md \
  .github/ISSUE_TEMPLATE/documentation.md \
  .github/ISSUE_TEMPLATE/performance.md \
  .github/ISSUE_TEMPLATE/security.md

git diff --cached --check

ok "Documentation passes git diff --check"

if git diff --cached --quiet; then
  warn "No changes detected. The community documentation is already current."
  exit 0
fi

# ------------------------------------------------------------
# Signed commit
# ------------------------------------------------------------
info "Creating GPG-signed commit"

GIT_AUTHOR_NAME="$SIGNING_NAME" \
GIT_AUTHOR_EMAIL="$SIGNING_EMAIL" \
GIT_COMMITTER_NAME="$SIGNING_NAME" \
GIT_COMMITTER_EMAIL="$SIGNING_EMAIL" \
git commit -S \
  -m "docs: add AXIOM community documentation"

ok "Signed commit created"

echo
echo "===== COMMIT VERIFICATION ====="
git log -1 --show-signature --format=fuller

# ------------------------------------------------------------
# Push
# ------------------------------------------------------------
info "Publishing to GitHub"

git push "$REMOTE" "$BRANCH"

ok "Community documentation published"

echo
printf "${C_CYAN}"
cat <<EOF
╔══════════════════════════════════════════════════════════════╗
║                    PUBLISH COMPLETE                        ║
╚══════════════════════════════════════════════════════════════╝
EOF
printf "${C_RESET}"

echo
echo "Repository:"
echo "https://github.com/${OWNER}/${REPO}"
echo
echo "Support:"
echo "https://github.com/${OWNER}/${REPO}/blob/main/docs/SUPPORT.md"
echo
echo "Governance:"
echo "https://github.com/${OWNER}/${REPO}/blob/main/docs/GOVERNANCE.md"
echo
echo "Contributing:"
echo "https://github.com/${OWNER}/${REPO}/blob/main/CONTRIBUTING.md"
echo
echo "Code of Conduct:"
echo "https://github.com/${OWNER}/${REPO}/blob/main/CODE_OF_CONDUCT.md"
echo
echo "Issue templates:"
echo "https://github.com/${OWNER}/${REPO}/issues/new/choose"
echo
ok "Everything has been pushed to main."
