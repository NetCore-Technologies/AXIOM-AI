# Archived repository artifacts

This directory preserves historical development artifacts that were accidentally kept alongside the active product sources.

## `legacy-feature-pack/`

This is an archive of an earlier roadmap feature-pack bundle: its manifest, scope/QA notes, status snapshot, and source overlay. It is kept only for historical comparison. It is not an installable patch, does not represent current test status, and must not be applied over the current checkout. Current implementation sources live under `axiom/`; active product documentation lives under `docs/`; the current scoped roadmap is `ROADMAP.md`.

The archived manifest describes the original feature-pack package and may reference files or hashes from that package rather than this archived layout.

## `.archive/patch-backups/`

These are snapshots created while editing files. They are not loaded by the application or release workflow. The authoritative current files are outside this directory; use Git history to inspect previous revisions. Backups are retained here only to avoid silently discarding the tracked snapshots during repository cleanup.

## Empty artifacts removed

Two empty root-level artifacts (`axiom-ui@0.1.1` and `tsc`) were removed because they contained no data and were not project source, configuration, or build inputs.
