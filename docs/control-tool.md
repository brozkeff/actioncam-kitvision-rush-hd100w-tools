# Python camera control CLI

Connect the host to camera Wi-Fi. No root shell or vendor library is required
for these commands; the Python client implements the binary protocol and its
legacy challenge/response login. See [wire specification](protocol/control.md).

```sh
uv run python tools/control.py info
uv run python tools/control.py status
uv run python tools/control.py settings
uv run python tools/control.py clock get
uv run python tools/control.py clock set --now --dry-run
uv run python tools/control.py clock set --now
uv run python tools/control.py clock set --at 2026-11-05T22:42:08
```

Clock set writes the recording processor clock, not the Wi-Fi Linux system
clock. Readback is displayed. Years must be 1970–2069. A naive --at value means
literal local wall time; an offset-aware value is converted to the host's local
timezone. No timezone or DST rules are stored on the camera.

Status returns battery percentage, recording state, mode and raw data as JSON.
Info returns protocol, camera model and both firmware versions. Settings reads
resolution, mode, language, clock and other exposed settings without modifying
them. Auto-power values remain raw because their duration mapping is unknown.
Use `--host ADDRESS` before
the subcommand to override 192.168.1.2. Invalid replies and timeouts return a
nonzero exit code; writes are never automatically repeated.

## Modes and experimental recording

Stop the webcam producer first. Mode changes may detach SD storage or stop
preview and must not overlap media downloads or other control clients.

```sh
uv run python tools/control.py mode realtime
uv run python tools/control.py record start
uv run python tools/control.py record stop
uv run python tools/control.py mode storage
```

Real_Time mode switching succeeded once, but a later attempt returned `0xff`
and left the camera in `Mass_Storage`. Recording commands match the APK but
have returned error `0x8d` from this camera. These operations are experimental,
not a verified working recording feature. The start command requires Real_Time
and skips an already-recording camera; stop skips an already-stopped camera.
If a write times out, reconnect and run status before repeating it. A failed
session is closed to prevent stale replies from matching a later request.

Clock persistence after reboot and new-media EXIF timestamps still require a
hardware acceptance test. Do not mistake successful command acknowledgement
for a finished file on the card.
