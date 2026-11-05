# Changelog

## [Unreleased]

## [0.0.1] - 2026-11-06

Initial experimental version. Clock setting has been verified by readback;
recording and reliable Real_Time mode switching remain unresolved.

### Added

- Discovery documentation, evidence inventory and offline APK inspection tools.
- Wi-Fi service map, settings layout, binary header findings, and verified
  MJPEG endpoints.
- Python 3.15 uv environment and read-only service/snapshot prototypes.
- Preview activation and capture sequence, including legacy CGI timeout handling.
- Linux webcam launcher with MJPEG passthrough, bounded retries and device cleanup.
- Detailed security exposure, architecture and webcam operation guides.
- Binary control framing, legacy authentication, status and clock CLI.
- Public hardcoded protocol values and hardware test results.

### Fixed

- Default webcam transport uses complete JPEG snapshots with transient retry,
  avoiding unreliable multipart framing; retain direct stream as an option.
