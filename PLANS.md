# Implementation ledger

- [x] Establish public/private repository boundaries and EUPL-1.2 licensing.
- [x] Inspect USB descriptors and supplied application symbols.
- [ ] Reconstruct configuration parser, serializer and clock apply sequence.
      Mac parsing, date record and rewrite behavior traced; obtain a real
      configuration and verify camera-side application before implementing writes.
- [x] Inspect SD through external reader and later list it through camera FTP.
- [x] Back up camera-generated configuration if located.
- [ ] Reconstruct Wi-Fi framing, authentication, ports and essential commands.
- [x] Connect via secondary Wi-Fi adapter and capture read-only diagnostics.
- [x] Copy persistent firmware files and scan all TCP ports.
- [x] Reconstruct partial binary frame and normalized settings layouts.
- [x] Verify binary framing, login, status and read-only settings queries.
- [x] Distinguish Linux clock from the camera clock and implement direct clock I/O.
- [ ] Validate clock write, unplug sequence and persistence after power cycle.
- [ ] Check physical REC switch with inserted card after software error 0x8d.
- [ ] Investigate intermittent Real_Time mode rejection `0xff`; identify the
      conditions required for mode switching and recording.
      In UVC, status and clock work but mode-get also returns `0x8d`;
      repeat card checks in an appropriate mode with physical state known.
- [ ] Trace port 8084 request parsing, supported methods and paths in the active
      `/bin/http` binary, including camera-device and realtime mode calls.
- [ ] Trace the Android app's realtime startup and control commands; it calls
      `ProtocolSwitchRealtime` (family 255, command 3, `Real_Time`, timeout
      10000), waits two seconds and opens `/?stream`; trace remaining setup.
- [ ] Reconstruct the dumped uClibc links in an isolated environment and use
      QEMU, syscall tracing and multiarchitecture GDB to investigate `/bin/http`.
      Account for the unavailable proprietary `/dev/CAM00` device.
- [ ] Trace the `remote` realtime mode implementation and camera device interface.
- [ ] Compare a bounded live 8084 response with the app's startup sequence once
      the relevant mode transitions and camera state are understood.
- [ ] Validate three recording start/stop cycles and playable output.
      Three files decoded after battery-powered tests; one stop reply was
      mismatched, although a fresh status showed stopped. Repeat that cycle.
- [ ] Investigate the managed-recording hang and failed stop before further
      hardware recording tests; a brief physical reset recovered the camera.
- [x] Add uv/Python 3.15 diagnostics and snapshot prototypes.
- [x] Verify preview activation POST and add bounded activation/capture commands.
- [x] Implement clock read/write and verify readback within one second.
- [x] Implement experimental recording commands; rejection 0x8d remains open.
- [x] Keep Python for orchestration and protocol; defer Rust without measured need.
- [x] Test preview failures, JPEG validation and webcam device lifecycle.
- [x] Verify MJPEG passthrough and five-frame V4L2 readback.
- [x] Document confirmed HTTP/FTP/Telnet exposures and Python direction.
- [ ] Validate automatic webcam allocation on a recent loopback module.
- [x] Add binary fixtures, framing, timeout invalidation, login and clock tests.
- [ ] Audit tracked content before any public release.

Future: desktop GUI, Windows/macOS adapters, modern native Kotlin Android client.
No iOS work planned. Firmware flashing, factory reset and formatting excluded.
