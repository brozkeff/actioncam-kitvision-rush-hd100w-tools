# Changelog

<!-- markdownlint-disable MD024 -->

## [Unreleased]

### Added

- Record owner confirmation that the generated status page exposes Wi-Fi
  credentials, Android app network metadata behavior, and a preliminary
  Windows app inventory; map read-only targets on 8083 and analyze the 8084
  camera HTTP service.

## [0.0.9] - 2026-11-06

### Changed

- Share control command execution between the CLI and GUI without launching a
  separate process for each GUI operation.

## [0.0.8] - 2026-11-06

### Added

- Document the observed physical reset recovery after a recording hang.

## [0.0.7] - 2026-11-06

### Added

- Managed recording CLI and GUI controls that select a local destination,
  identify a new camera video and download it after stopping.

## [0.0.6] - 2026-11-06

### Added

- Document the backed-up camera configuration and battery-powered recording
  tests, including a mismatched stop reply and decoded media.

## [0.0.5] - 2026-11-06

### Added

- Document read-only UVC mode, clock, settings error and storage observations.

## [0.0.4] - 2026-11-06

### Added

- Document the macOS application's USB configuration paths, record parsing,
  clock record serialization and file rewrite limitations from disassembly.

## [0.0.3] - 2026-11-06

### Added

- Save a camera JPEG from the GUI using a file selection dialog.

## [0.0.2] - 2026-11-06

### Added

- Experimental Tkinter camera controller with background status and clock
  polling, command output, recording controls and a live JPEG preview.
- Pillow dependency for displaying preview images.
- README screenshot showing the experimental controller.

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
