# Protocol discovery

## USB configuration: observed static evidence

Mac binary contains `_readAllConfig`, `_getConfig`, `_saveConfigLine`,
`_setConfigLine`, clock UI handlers, `/ActionConfig` and `/ActionCamera.bin`.
`_saveConfigLine` opens the configured path with `w+` and serializes selected
configuration lines using `%s\n`. Exact file roles and field meanings remain
unverified. Do not write either candidate file based on its name alone.

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
