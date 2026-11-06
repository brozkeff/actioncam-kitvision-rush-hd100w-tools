# Protocol discovery

## USB configuration: observed static evidence

The supplied macOS executable constructs `ActionConfig` beside the
`actionplus.app` bundle by stripping `/actionplus.app` from its executable
path. It also constructs a sibling `ActionCamera.bin` path. A missing
`ActionConfig` causes a connection-failed dialog; its
`CreateDefaultConfigFile` method is empty. This explains why simply starting
the app elsewhere does not establish a camera configuration file. The paths
are derived from the application location, not from a discovered SD mount.

Static reconstruction of this particular executable (addresses are virtual
Mach-O addresses):

- `_readAllConfig` at `0x100005d50` uses `fgets` with a 100-byte buffer and
  processes at most 99 chunks. It finds `[` and `]` anywhere in a chunk,
  retains text starting at `[`, and classifies its first two decimal fields.
  `[1,1,...]` through `[1,4,...]` become types 1–4; a first field of 2
  becomes type 5. Other lines are unclassified. Long lines may be split.
- `_getConfig` at `0x1000061e0` parses the first recognized instance of
  each type. Type 3 scans 13 integers, adding 1970 to its year field.
  The serializer at `0x100006e61` writes type 3 as
  `[1,3,A,B,C,D,day,month,year_minus_1970,hour,minute,second,E,]`.
  `A`–`E` are other settings whose meanings remain to be verified. The
  date picker handler supplies calendar date and time components; the file
  month and day are not decremented in this code path.
- The date confirmation handler at `0x10000d090` updates type 3 and calls
  `_saveConfigLine`. That function opens `ActionConfig` with `w+` and writes
  only classified types 1–5 using `%s\n`; unclassified lines are dropped.
  Rebuilt type 3 retains the other decoded settings, but does not preserve
  arbitrary original text or extra fields. If type 3 is absent, the setter
  does not construct a valid replacement type 3 in the observed branch.
- Type 5 serialization includes the literal `ActionCamera.bin`; this does
  not establish that file's contents or its role in applying settings.

These are static findings, not a verified camera file or safe write recipe.
On 2026-11-06, after the user restarted the camera on battery and took a photo,
`ActionConfig` appeared at the card root alongside `actionplus.app`. A private
158-byte backup is in ignored `tmp/camera/config-backups/`. Its type 3 record
contains one further numeric field after the 13 fields parsed above, confirming
that rewriting it with the legacy serializer would discard information. The
file's clock fields differed from a contemporary live clock query; their update
and apply timing remain unknown. Do not rewrite the file until camera-side
behavior is verified.

The original manual requires immediate USB disconnection after clock setting:
[HD100W manual][manual]

Trace path construction, parser, serializer and date handlers; compare actual SD
files. Preserve unknown fields and back up before writes. Determine when a staged
timestamp takes effect and whether it represents local wall time or UTC.

## Wi-Fi: observed static evidence

APK `lib/armeabi/libaction.so` exports `WiFiJNI` functions for status, battery,
recording, settings and mode switching. Strings include `192.168.1.2`;
DEX includes `http://192.168.1.2:8084/?stream`.
Native code is ARM Thumb: use `llvm-objdump-14 -d
--triple=thumbv7-linux-gnueabi` rather than default ARM decoding.

The reconstructed protocol, login and command results are documented in
[binary control](control.md). Do not assume Ambarella JSON compatibility.

## Hardware experiments

Connect only to the identified camera through a secondary adapter; retain the
existing default internet route. Start with identity/status queries. If a shell
is available, inspect services, processes, mounts and clocks read-only. Do not
assume setting Linux system time changes the recording processor clock.

Then validate explicit clock and recording operations. After timeout, report
unknown state and query before retrying recording. Verify timestamps using a new
photo and test persistence after power cycling. Clock acceptance: within five
seconds of host time after the documented apply sequence. Recording acceptance:
three successful short cycles with matching status and playable output.

[manual]: https://device.report/m/bee9151d39c938d7bad6b570e8940904473f0a560ad0191af17082b189655fa2

## Current implementation boundary

Preview activation, snapshots and Linux virtual-webcam transport now work in
Python. See [preview findings](preview.md) and [webcam operation](../virtual-webcam.md).
The binary recording-clock write has been verified by readback; persistence and
timestamps in new media remain to be tested. USB configuration paths remain
research leads. Binary recording commands and mode switching are experimental;
see [control results](control.md) for observed failures.
