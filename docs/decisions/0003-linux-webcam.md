---
status: Accepted
date: 2026-11-05
---

# Reuse Linux webcam components

## Context and Problem Statement

The camera exposes preview frames over HTTP but does not appear as a USB
webcam. Linux applications expect a video capture device, and the camera's
multipart stream has stalled during testing. The launcher should be usable
alongside existing webcams and clean up devices it creates.

## Decision Outcome

Use Python to activate preview, fetch complete JPEG snapshots by default and
supervise FFmpeg. FFmpeg sends MJPEG to an existing v4l2loopback kernel driver;
YUYV output and direct multipart stream input remain options. Python does not
decode or re-encode the MJPEG frames itself.

When supported, allocate a free virtual device with `v4l2loopback-ctl`, request
exclusive capabilities and delete that device on exit. An existing loopback can
be selected explicitly and is never deleted by the launcher. Do not reload or
replace a loaded module merely to obtain dynamic allocation.

## Alternatives Considered

- **New kernel driver:** duplicates v4l2loopback functionality and increases
  maintenance and platform-specific work without a demonstrated need.
- **Direct multipart stream as the default:** is simpler but has timed out and
  produced corrupt input packets on the tested camera; it remains selectable.
- **Decode each frame in Python:** adds work and dependencies when FFmpeg can
  handle the video path and copy MJPEG for compatible consumers.

## Consequences

FFmpeg, v4l-utils, v4l2loopback and suitable host permissions are prerequisites.
Existing-device MJPEG and YUYV output have been verified on the development
host. Dynamic allocation requires a newer loopback control interface and has
not yet been verified on that host; automated tests cover allocation arguments
and cleanup behavior. Preview and recording compatibility remain unverified.
The choice complements [ADR 0002](0002-python-prototypes.md).
