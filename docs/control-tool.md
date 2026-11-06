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

To record and copy one new video locally, use:

```sh
uv run python tools/record.py
uv run python tools/record.py --host 192.168.1.2 --output captures/my-video.mov
```

Press Enter to stop. The default is a timestamped MOV in the current
directory; a specified parent directory must already exist. Existing files
are never replaced. The GUI's **Start recording…** asks for a local filename
first; **Stop and save** ends the recording and downloads it. Keep the window
open until saving completes. Both workflows switch to storage mode to list
existing videos, switch to Real_Time to record, then return to storage to
identify and download the single new MOV. The original stays on the card.
Concurrent capture on the camera or another client can make identification
ambiguous; in that case the workflow refuses to choose a file. If stop cannot
be verified, it leaves the mode alone and asks for a status check. A failed
or interrupted session may leave a recording on the camera; inspect it before
retrying. The camera may not vibrate or change LED colour for remote recording,
as observed by the owner; use status rather than the indicator to check it.

```sh
uv run python tools/control.py mode realtime
uv run python tools/control.py record start
uv run python tools/control.py record stop
uv run python tools/control.py mode storage
```

Real_Time mode and recording have worked on battery with an exposed card, but
mode switches and commands have also returned errors. These operations remain
experimental. The start command requires Real_Time
and skips an already-recording camera; stop skips an already-stopped camera.
If a write times out, reconnect and run status before repeating it. A failed
session is closed to prevent stale replies from matching a later request.

Clock persistence after reboot and new-media EXIF timestamps still require a
hardware acceptance test. Do not mistake successful command acknowledgement
for a finished file on the card.
