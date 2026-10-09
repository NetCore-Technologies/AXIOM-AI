# Changelog

## 0.2.0-beta.7 — unreleased preparation

This section describes the beta.7 target. It is not a claim that release
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
