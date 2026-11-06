# Camera network exposure and safe operation

## What was actually verified

These observations concern this Rush HD100W and its 2013 Wi-Fi firmware. They
are not claims about every Kitvision model or firmware revision. All access was
to the owner's camera at `192.168.1.2` with permission. No destructive testing,
firmware flashing, credential changes or card formatting was performed.

Wi-Fi association and service authentication are separate boundaries. The camera
may require a Wi-Fi password; that does not protect it from another client who
already joined its hotspot. We did not demonstrate Wi-Fi encryption bypass.

| Port | Verified access | What it enables |
| --- | --- | --- |
| TCP 21 | FTP login `ap71` with empty password | Filesystem downloads |
| TCP 23 | Telnet login `root` / `root` | Administrative Linux shell |
| TCP 80 | HTTP, no authentication on tested URLs | UI and filesystem reads |
| TCP 6667 | Open binary control listener | Fixed shared login, now verified |
| TCP 8080 | No-auth JPEG and MJPEG when preview active | Live camera viewing |
| TCP 8083 | HTTP, no authentication on tested URLs | Filesystem reads |
| TCP 8084 | Camera HTTP/file-stream service | `/bin/http` static bind; APK stream target; HTTP 200 observed, body stalled |
| TCP 53 | Open listener; dnsmasq running | DNS candidate, behavior untested |

TCP 8080 was initially closed and opened after preview activation, so it is
additional to the seven services found by the original full TCP scan. UDP was
not scanned; these results do not imply an absence of UDP services. Nmap's IRC
label for 6667 is incorrect for this binary protocol.

## Evidence and boundaries

- FTP downloaded 255 persistent files, including native control programs and
  configuration, totaling 7,637,620 bytes. Raw contents remain in ignored tmp/.
  FTP write/delete privileges were not tested. Its empty-password login is
  weaker than anonymous access protected by a separate secret.
- Telnet provides a root BusyBox shell. The initial shell showed an epoch clock,
  processes, mounts and kernel logs. Telnet has no transport encryption.
- The root filesystem is read-only squashfs. This limits direct persistent file
  edits but does not make a root shell safe: RAM filesystems, devices, services
  and privileged control interfaces remain accessible.
- Unauthenticated GET `/etc/inittab` returned 89 bytes on both HTTP ports 80
  and 8083, exactly matching the dump. GET `/bin/remote` on 8083 returned the
  matching 78,320-byte binary. This is direct filesystem exposure, not just an
  inference from document-root configuration. Sensitive file URLs were not
  needed for this test and are not reproduced in published notes.
- The generated `/tmp/www/ver.html` page was opened on the camera at port 8083
  and showed the configured SSID and passphrase, along with firmware details.
  The owner redacted credentials from the shared response. See the
  [verified status-page finding](findings/2026-11-06-status-page.md).
- POST `/cgi-bin/uvc` needed no HTTP login and activated preview. A timeout did
  not mean failure: the service subsequently delivered JPEG frames on 8080.
- Both snapshot and multipart MJPEG endpoints delivered frames without login.
  They expose whatever is in front of the lens while the camera is reachable.
- The remote binary contains CHAP, protocol-family switching and verification
  logic. An open port does not establish that every control command is accepted
  without authentication. A subsequent legitimate login succeeded using
  fixed username APPIOS and shared secret 12345678; see the public control
  specification. Recording commands were tested but rejected with status 0x8d.
- Firmware startup contains update/recovery mechanisms, and control binaries
  contain format, reboot and power-off paths. Their existence combined with
  root access presents serious tampering risk; destructive use was not tested.

Evidence files are indexed in [Wi-Fi capture notes](findings/2026-11-05-wifi-capture.md).
The HTTP exposure test is saved at ignored `tmp/camera/http-read-exposure.json`.

## Consequences for anyone joining the hotspot

A joined client can use the confirmed service exposures to view live preview,
read camera software and configuration, and obtain a root shell with the known
credentials. Depending on current operating mode and command support, an
attacker could interrupt services or interfere with camera operation. Root
access can also support harmful changes to writable configuration or firmware;
that impact is a threat assessment, not a performed experiment.

There is no demonstrated separation between the normal companion-app user and
an administrator. The default shell credentials are not an authorization check
against someone who knows this camera. Changing the hotspot password alone does
not address exposures after another client joins. The Linux build is from 2013;
we have not performed a comprehensive vulnerability assessment.

## How this supports the replacement application

- Plain HTTP MJPEG provides a verified SDK-free video source. Python performs
  mode activation; FFmpeg handles frames and the standard Linux loopback driver
  exposes a webcam to applications.
- FTP is useful for owner-authorized research and evidence capture. It is not
  needed in the normal preview or webcam path.
- Telnet enables read-only investigation of the processor boundary and clocks.
  The companion app should not rely on an unrestricted root shell for routine
  recording or clock operations.
- TCP 6667 is the intended control research target. Implement its verified
  request/response protocol after resolving framing and authentication.
- HTTP filesystem reads allow independent inspection of firmware files without
  installing additional camera software. Downloaded code is analyzed, never
  executed on the host.

## Operating recommendations

- Enable the hotspot only while needed, use a strong unique hotspot password
  where supported, and assume any other joined client has substantial access.
- Keep the camera on its own Wi-Fi interface/subnet. Disable automatic joining
  and sharing/bridging of this connection. Keep the normal internet route on
  Ethernet; do not expose camera services through port forwarding or a VPN.
- Do not enable host IP forwarding or hotspot sharing to make the camera's
  network reachable by other computers. Host firewall policy remains relevant.
- Do not treat the camera as secure for private locations merely because the
  vendor apps are obsolete or unavailable.
- Use explicit camera IPs and bounded timeouts. Preview startup changes device
  mode; it must not be mistaken for a passive status query.
- Keep dumps, personal frames, passwords, firmware and raw captures out of Git.
  Public docs include the confirmed factory shell/FTP credentials intentionally
  to explain the exposure; they must not include users' actual Wi-Fi passwords.

These prototypes improve usability; they do not harden or patch the camera.

## Subsequent control authentication verification

The fixed values are intentionally public: username `APPIOS`, ASCII shared
secret `12345678`, MD5 over a 12-byte challenge concatenated with that secret.
This handshake was reproduced successfully, followed by authenticated status,
mode and recording-clock operations. Details and command IDs are in the
[control specification](protocol/control.md). These constants do not depend
on the user's Wi-Fi password and cannot provide a secret known only to the
owner. The Python client follows the handshake rather than relying on Telnet.
