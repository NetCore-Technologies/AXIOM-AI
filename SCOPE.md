# Roadmap scope notes

This pack is deliberately small relative to the 120-item backlog. It advances foundations and creates a trustworthy GUI status surface; it does not complete all unchecked items.

| Related item | How this pack advances it | Status treatment |
|---|---|---|
| R002 — workspace discovery | `discover_workspace_root` supports explicit workspace, `AXIOM_WORKSPACE`, nearest project marker, then current directory; it rejects a symlink target. | Partial integration; do not mark complete until workspace discovery is consistently reused across all CLI/API paths. |
| R010 — workspace health checks | Read-only checks cover config structure, project paths/symlinks, read/write access, disk headroom, Python version, and required modules. | Partial, tested in isolation; verify behavior in supported platform environments. |
| R011 — retention/storage/deletion documentation | The guide documents local, read-only diagnostics and support-bundle exclusions. | Partial documentation; does not replace a complete retention/deletion policy for all stores. |
| R014 — JSON output parity | `doctor`, `status`, `config validate`, roadmap audit, and support-bundle creation provide machine-readable results. | Partial; other existing list/inspect commands still need consistent JSON contracts. |
| R019 — workspace-aware status | `axiom status --json` includes diagnostics and Git metadata. | Partially implemented; validate from a real nested project checkout before marking complete. |
| R022 — config validation | Validation checks bounded YAML parsing and section types without echoing configuration values. | Partial; safe repair suggestions remain a broader follow-up. |
| R023 — stable failure codes/documentation | New CLI commands use stable JSON envelope fields and distinct non-zero exit conditions. | Partial; a repo-wide exit-code contract remains unfinished. |
| R025 — preserve the Control Center | The Roadmap page and Diagnostics additions use the current page/layout primitives and existing CSS; `src/styles.css` is not edited. | Styling preservation intent is implemented in the patch, but screenshot/browser regression validation remains outstanding. |
| R035 — export/download affordances | The GUI downloads a named support ZIP, with no-store response headers and documented privacy boundaries. | Partial; this covers support bundles rather than every export surface. |
| R115 — configuration/path/dependency/storage diagnostics | Structured, stable-ID diagnostics cover these local checks. | Partial; broader package, API, and runtime checks remain. |
| R116 — support bundle | API and CLI export only allow-listed diagnostics/environment metadata with explicit exclusions. | Implemented in this feature slice, pending full-repository/platform validation. |
| R120 — E2E acceptance coverage | Focused API/core/CLI tests were added. | Not complete; Playwright E2E and cross-workflow acceptance still need a real checkout. |

No `ROADMAP.md` item label is changed by this pack. This prevents unchecked items from appearing complete before the full release gates pass.
