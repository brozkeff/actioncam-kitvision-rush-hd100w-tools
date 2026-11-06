# Technical documentation

## Start here

- [Hardware and modes](hardware/camera.md).
- [Camera filesystem and service versions](hardware/filesystem-services.md).
- [Network security and exposure](security.md).
- [Architecture and implementation direction](architecture.md).
- [Camera clock/status/control CLI](control-tool.md).
- [Linux virtual webcam setup and operation](virtual-webcam.md).

## Protocols

- [Public fixed addresses, credentials and constants](protocol/constants.md).

- [Verified binary control and hardcoded compatibility values](protocol/control.md).

- [Discovery approach and USB configuration leads](protocol/discovery.md).
- [Wi-Fi services, binary header and settings layout](protocol/wifi-control.md).
- [Verified preview endpoints and activation sequence](protocol/preview.md).

## Evidence and experiments

- [Reference binary hashes](findings/inventory.md).
- [External SD inspection](findings/2026-11-05-external-card.md).
- [Wi-Fi capture and clock distinction](findings/2026-11-05-wifi-capture.md).
- [Boot and runtime analysis](findings/2026-11-05-boot-analysis.md).
- [Generated status-page credential disclosure](findings/2026-11-06-status-page.md).
- [Port 8083 filesystem paths and app endpoint references](findings/2026-11-06-http-filesystem.md).
- [Port 8084 service and static endpoint analysis](findings/2026-11-06-port-8084.md).
- [Android app network behavior](findings/2026-11-06-android-app.md).
- Original USB observations are summarized in [hardware and modes](hardware/camera.md).

Raw evidence lives in ignored tmp/camera/, not in the public repository.
Historical notes describe their experiment time; a port closed in one test
may be open in a later camera mode.

## Decisions

- [0001: Discovery before tooling](decisions/0001-discovery-first.md), superseded.
- [0002: Python prototypes before Rust](decisions/0002-python-prototypes.md).
- [0003: Reuse Linux webcam components](decisions/0003-linux-webcam.md).

Evidence labels: observed means directly inspected; inferred is a working
hypothesis; verified requires a successful hardware experiment. Each experiment
should identify source, command, firmware, mode and outcome. Static reconstruction
alone is insufficient evidence that a write command is safe or effective.
