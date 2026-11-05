# Verified binary control and public compatibility constants

## Connection and frame layout

- TCP endpoint: camera `192.168.1.2`, port `6667`.
- One command at a time per connection; parse TCP as a byte stream, not one
  recv call per frame. The Python client checks lengths, checksum, family,
  command and sequence. It closes a session after an error to discard late replies.
- Little-endian fields are verified on this firmware, protocol version `0x13`.
- Frame: `DAEH`, uint16 total length, uint8 sequence, uint8 family,
  uint16 command, uint16 command timeout field, payload, uint16 checksum.
- Base frame size is 14 bytes; maximum accepted by this client is 2048.
- Sequence wraps at 256; reply command is request command OR `0x8000`.
- Replies start their payload with a status byte: zero means acknowledged.
- Checksum is the one's complement of a folded sum of little-endian uint16
  words over everything before the trailer. For an odd byte count, the final
  byte occupies the low byte of a zero-padded word. Trailer is little-endian.
- The APK uses timeout-field 200 for ordinary queries and 10000 for recording
  and mode changes. Do not reuse the short query timeout for long operations.
- Writes are never retried automatically. After a timeout, reconnect and inspect
  status; the operation may already have happened.

Verified version exchange, hex:

```text
request: 444145480f0001000100c800009d75
reply:   444145481000010001800000001363e3
```

This small protocol fixture is also an automated test; it is not copied app code.

For the full fixed-value inventory, see [public constants](constants.md).

## Hardcoded authentication values: intentionally public

These are constants embedded in the shipped Android app and camera firmware,
not private credentials supplied by a user. They are documented openly for
interoperability and because they do not provide meaningful secrecy.

| Value | Meaning |
| --- | --- |
| `APPIOS` | Fixed client username, padded with NUL to 16 bytes |
| `12345678` | Fixed eight-byte shared secret, ASCII |
| MD5 | Legacy digest algorithm, not a recommendation for new authentication |
| 6 bytes | Client identity tag; Python generates a locally administered tag |
| 12 bytes | Camera challenge returned in the first login reply |

Login on the same TCP connection:

1. Family 0, command 2, payload = six-byte client tag. Read status plus the
   12-byte challenge.
2. Family 0, command 3, payload = `APPIOS` padded to 16 bytes. Require status 0.
3. Family 0, command 4, payload = raw 16-byte MD5 digest of
   `challenge || ASCII("12345678")`. Require status 0.
4. Issue camera commands on the authenticated connection.

This sequence succeeded on hardware. The UI call path confirms start/stop use
WiFiJNI.sendVideoStart/sendVideoStop and native commands 6/7. The digest and
username must not be confused with the hotspot WPA password, Telnet password,
or FTP login. No random challenges or user-specific Wi-Fi passwords need to be
published. Knowing these fixed values permits compatible clients to authenticate;
see [security implications](../security.md).

## Command map and evidence

| Family | Command | Operation | Hardware result |
| --- | --- | --- | --- |
| 0 | 1 | Protocol version (payload one zero byte) | `0x13` |
| 0 | 2, 3, 4 | Challenge, username, digest | Login succeeded |
| 1 | 1 | Camera firmware | `V1.3.10.020` |
| 1 | 2 | Camera model | `SV5AW` |
| 1 | 3 | Camera status | Mode, battery, recording flags read |
| 1 | 6 | Recording start | Rejected with `0x8d`; unresolved |
| 1 | 7 | Recording stop | Rejected with `0x8d` during tests |
| 1 | 8 | Photo resolution | `5MP` |
| 1 | 9 | Photo mode | `single` and interval data |
| 1 | 10 | FHD resolution | `1080P30` |
| 1 | 11 | HD resolution | `720P60` |
| 1 | 12 | TV system | `PAL` |
| 1 | 13 | Recording clock get | Twelve ASCII digits |
| 1 | 14 | Auto power setting | `3`; duration meaning unresolved |
| 1 | 15 | Auto rotation | `disable` |
| 1 | 16 | Language | `English` |
| 1 | 17 | Mode get | `Mass_Storage` before switch |
| 1 | 25 | Recording clock set | Acknowledged and read back correctly |
| 2 | 1 | Wi-Fi firmware version | `3.0.00.030` |
| 255 | 3 | Mode switch (12-byte padded name) | Once OK; later `0xff` |

Camera status data after removing the reply status byte:

- Byte 0: flags; bit 0 indicates recording, bit 1 is another app mode flag.
- Byte 1: battery percentage (observed roughly 25–37 in these experiments).
- Bytes 2–13: NUL-padded mode name, e.g. Mass_Storage or Real_Time.
- Further bytes may be present; Python retains raw hex for diagnostics.

Do not confuse the byte-0 reply status with byte-0 status-data flags. The early
raw labels in console experiments were reversed; the production client uses
battery at data offset 1 and recording flags at data offset 0, confirmed against
ProtocolHostInfo1 in the APK.

## Recording clock format and successful correction

- Payload is 12 ASCII decimal digits: `YYMMDDhhmmss`.
- YY means calendar year minus 1970, not calendar year modulo 100.
- Month and day are ordinary one-based decimal values in this representation.
- This differs from the earlier 14-byte normalized settings structure, whose
  month/day are zero-based. Do not send that structure to command 25.
- Example: `561105224208` means 2026-11-05 22:42:08.
- This clock has no timezone field. Use local wall time for media timestamps.
- Before correction, camera reported `561106002758`; setting it to host local
  time returned success, then readback `561105224209` approximately one second
  after writing `561105224208`.
- Clock writes do not replace the other camera settings or use Linux date -s.
- Power-cycle persistence and timestamps in newly captured media remain pending.

## Recording failure investigation

- SD was inserted, and its files were listed over FTP while in Mass_Storage.
- Clock setting worked with SD inserted.
- Recording start initially timed out; a later reply could not safely be reused
  for stop. The client now invalidates failed sessions.
- A fresh status query confirmed recording=false; a fresh stop request returned
  error `0x8d`. No successful recording start was observed.
- Switching to Real_Time succeeded and re-enumerated the internal camera USB
  as Ambarella `4255:0001`, Amba Simple Class. This confirms the internal USB
  mode boundary that was previously inferred.
- On 2026-11-06, switching to `Real_Time` returned `0xff` on repeated attempts;
  status showed `Mass_Storage`, recording false and battery 100%. The cause
  and meaning of this status are unknown. A storage-mode command succeeded.
- Recording with the APK's exact 10000 timeout field still returned `0x8d`.
  The camera Linux log showed SPI slave receive timeouts. Do not label this
  error as definitely no SD, authentication failure, or low battery.
- The Real_Time HTTP endpoint on 8084 returned status 200 and
  application/octet-stream but supplied no 4096-byte body before timeout.
- The APK-derived space query (family 255, command 32, selector 0, timeout
  field 1000) also timed out in Real_Time. It is not exposed as a supported
  command in the public CLI yet.
- Physical REC-switch testing, card recognition, power state and the legacy
  app's prerequisites need further investigation. Three playable recordings
  have NOT been verified; the CLI reports rejection rather than success.
