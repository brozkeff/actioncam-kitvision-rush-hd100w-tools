# Wi-Fi control: initial static reconstruction

This is the earlier reconstruction record. For hardware-verified framing,
authentication, commands and corrected status offsets, use
[the control specification](control.md). The 0x51/0x52 settings path below is a
legacy alternative, not the clock path used by the current client.

## Services (hardware observed)

Full TCP connect scan of `192.168.1.2`, all 65,535 ports, completed in 6.33 s.
Seven open ports; other 65,528 reported closed. No NSE scripts were run.
Port 8080 was later verified open after preview activation; the map below
describes the initial scan. See [security notes](../security.md) for verified
authentication and HTTP filesystem exposure.

| TCP port | Purpose | Evidence |
| --- | --- | --- |
| 21 | FTP | Successful file transfer |
| 23 | Telnet | Successful shell login |
| 53 | DNS candidate | Listener; dnsmasq running |
| 80 | Web interface | BusyBox httpd running |
| 6667 | Binary camera control | remote server initialization at `0x409da8` |
| 8083 | Static HTTP/media access | lighttpd.conf specifies port and root `/` |
| 8084 | Camera HTTP/file-stream service | active `/bin/http` bind, APK URL and observed HTTP response |

Nmap labels 6667 as IRC by port convention; this is not evidence of IRC.
Raw scan outputs: ignored `tmp/camera/nmap-tcp.*`.

## Processor boundary

- `/bin/remote` is a MIPS big-endian dynamically linked executable.
- It opens `/dev/remote`; settings operations use ioctl requests.
- `GetSetting` (`0x40c970`) uses ioctl `0xa1` with a 512-byte buffer.
- `SetSeting` (`0x40dd8c`, original misspelling) uses ioctl `0xa2`.
- Both check low 16 bits of returned buffer for `0x7ff0` or `0x7ff1` errors.
- A normalized settings structure is 14 bytes, not just a date payload.
- Date/settings network dispatch at `0x401e58` accepts command `0x51` (get)
  and `0x52` (set). Set requires at least 14 payload bytes.
- The kernel module `lib/rt_mode_class.ko` registers USB VID:PID `4255:0001`
  and exposes CAM0 devices. This differs from external mass storage `4255:1000`.
- Hypothesis: Wi-Fi MIPS board bridges commands to the recording processor over
  internal USB/custom driver. Exact `/dev/remote` driver still needs tracing.

## Protocol families

Static main-loop evidence in `/bin/remote`:

- TCP listener port 6667 with a 2048-byte receive buffer.
- Old family starts with byte `0x5a` (`Z`).
- New family uses magic bytes `44 41 45 48` (`DAEH`): explicitly assembled
  little-endian and compared with `0x48454144` at `0x40a2a4`.
- New-family dispatch inspects byte 7 and a byte-swapped 16-bit field
  at offset 8.
- `/tmp/host.new` and `/tmp/no_support.new` affect family negotiation.
- Do not send tentative frames yet: family detection can change camera mode.
- Full framing, checksum, authentication and reply semantics remain unresolved.

## Local command-line interface

Static `main` contains protocolversion, wifiversion, hostversion, hostname,
getmode, setmode, oldprotocol, newprotocol, convertprotocol, setting, detect,
angle, update, reboot and poweroff branches. This is NOT a verified usage guide.
Some commands are destructive or change recording/USB mode.
The record branch issues ioctl `0x78`; its argument token and start/stop semantics
still need validation. Do not treat the string `record` as a complete command.

## Reproduce offline analysis

Run `python3 tools/mips-analyze.py tmp/camera/rootfs/bin/remote
 tmp/camera/remote-analysis` as a single command. The helper restores synthetic
section headers in a separate ELF copy, invokes llvm-objdump-14 and annotates
static string/GOT references. Originals remain unchanged and are never executed.
Annotations are linear hints, not a decompiler or proof of reachable behavior.
All generated ELF copies and listings must stay inside ignored `tmp/`.

## Normalized settings bytes

Statically decoded from print routine `0x40b550` and GetSetting copy-out.
Not yet compared with a live successful camera-settings reply.

| Offset | Meaning | Encoding |
| --- | --- | --- |
| 0 | Photo resolution | Enum, mapping pending |
| 1 | Photo mode | Enum, mapping pending |
| 2 | FHD resolution | Enum, mapping pending |
| 3 | HD resolution | Enum, mapping pending |
| 4 | TV type | Enum, mapping pending |
| 5 | Auto power down | Enum, durations pending |
| 6 | Auto rotation | Enum |
| 7 | Format flag | Preserve; never enable for clock setting |
| 8 | Year | Calendar year minus 1970 |
| 9 | Month | Calendar month minus 1 |
| 10 | Day | Calendar day minus 1 |
| 11 | Hour | 0–23 |
| 12 | Minute | 0–59 |
| 13 | Second | 0–59 |

- The camera-side settings list is distinct from this normalized representation:
  parser `0x40c1f8` reads four-byte entries: big-endian 16-bit setting flag,
  one parameter byte, another parameter byte. Zero flag terminates the list.
- Flags `0x90` through `0xa0` dispatch through a jump table; strings identify
  resolution, mode, TV, auto power, frequency, date/time, rotation, language,
  version and format settings. Exact flag assignments need table reconstruction.
- Suspected firmware bug: parser hour/minute/second cases at `0x40c738`,
  `0x40c790`, `0x40c7e8` branch past storage when the value is nonzero.
  They appear to retain only zero values. Confirm against actual replies before
  trusting normalized readback or reusing the original conversion behavior.
- Auto power-down is a candidate explanation for shutdown, not a diagnosis.
  Read its current setting and map durations before considering any change.

## New-family header: partial layout

Static receive path and response builder `0x403f7c` establish these fields.
Byte-order conversion is conditional in the response builder; use actual APK
frames and captured replies to resolve negotiated behavior before implementation.

| Offset | Size | Meaning |
| --- | --- | --- |
| 0 | 4 | Magic, incoming bytes `44 41 45 48` |
| 4 | 2 | Total frame length |
| 6 | 1 | Sequence identifier |
| 7 | 1 | Command family/type |
| 8 | 2 | Command identifier |
| 10 | 2 | Reserved/header field, initialized zero in replies |
| 12 | variable | Payload; response starts with status byte |
| End − 2 | 2 | Checksum, algorithm still pending |

- Types 0, 1, 2 and 255 have separate dispatch paths.
- Replies add `0x8000` to command IDs in error paths (16-bit arithmetic).
- Error paths distinguish preamble, checksum, sequence, length and command type.
- A response with one status byte occupies 15 bytes (12 header + 1 + 2).
- Framing is binary; do not send text/IRC commands to port 6667.
