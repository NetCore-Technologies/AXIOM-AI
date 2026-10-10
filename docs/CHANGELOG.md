# Changelog

## [0.3.0-beta.1] — release preparation

- Align Python package metadata with the beta.1 version (`0.3.0b1`).
- Add an explicit feature implementation plan and acceptance criteria.
- Clarify which workflow improvements are foundations versus planned work.
- Preserve the existing Control Center UI; no redesign is included in this documentation/version-preparation change.
- Distribution publication and feature completion remain gated on passing CI and successful registry workflows.



## 0.2.0-beta.9

### Changed

- Optimizer, Quantization Lab and Beta.5 panels share the app theme tokens in dark and light mode.
- Quantization Lab shows an FP16, INT8 and INT4 size comparison against detected memory (rough estimate).

### Added

- Read-only daemon routes for the local workspace: `/api/models`, `/api/files`,
  `/api/model/inspect`, `/api/dataset/inspect`, `/api/train/plan`,
  `/api/ai/plan`, and `/api/headroom`.
- The daemon serves a bundled web UI at `/ui/` when `axiom/webui` is present.
- Release workflows build the web UI and bundle it into the Windows, Linux,
  macOS, and PyPI packages.
- PyPI publishing on version tags with a version-consistency check.

### Security

- Daemon workspace paths must resolve inside the working directory.
- Requests with a non-loopback `Host` header are refused unless the daemon was
  started with `--allow-network`.

### Fixed

- CodeQL alerts for modules imported with both `import` and `import from`.

## 0.2.0-beta.8 — release preparation

This section describes the beta.8 target. It is not a claim that release
assets, workflows, or hosted pages have passed live verification.

### Documentation and product contract

- Rewrote the first-minute CLI path around `axiom`, `guide`, `summary`, the
  model and dataset checks, hardware planning, and `tools doctor`.
- Documented the loopback-only daemon, operating-system port selection, and
  explicit network opt-in.
- Corrected examples for positional model metadata and dataset-clean output
  arguments.
- Separated shipped inspection/planning behavior from future training,
  inference, telemetry, and hosted-workspace work.
- Kept Linux bundle and Python fallback installation behavior explicit.
- Documented Headroom as an optional external context-compression proxy that
  AXIOM may explain or discover but never bundles or starts.
- Added an explicit Headroom status and passthrough path that never installs
  or starts the external proxy during discovery.
- Hardened Linux release installation with pinned tags, user-scoped paths,
  archive validation, and checksum verification.

## 0.2.0-beta.7

See the [published beta.7 release](https://github.com/NetCore-Technologies/AXIOM-AI/releases/tag/v0.2.0-beta.7)
for the assets and commit associated with that earlier prerelease.

## 0.2.0-beta.6

- Focused the Linux distribution on a reusable unpacked tarball for repeated
  terminal launches.
- Added checksum verification to the Linux bundle installer.
- Published Linux DEB, AppImage, one-file ELF, tarball, and installer assets
  when the release workflow completed successfully.
- Smoke-tested the version command, loopback daemon health route, bundle
  contents, DEB metadata, and installer syntax in CI.

## 0.2.0-beta.5

- Added optimizer and quantization planning foundations.
- Added filesystem-boundary hardening and expanded release validation.
- Documented the status of unsigned, unnotarized macOS distribution assets.
