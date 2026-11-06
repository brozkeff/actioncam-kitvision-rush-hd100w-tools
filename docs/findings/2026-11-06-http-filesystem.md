# Port 8083 filesystem access and app endpoint references

## What the dump and runtime evidence establish

The dumped `/etc/lighttpd.conf` sets document root `/`, binds to
`192.168.1.2:8083`, enables static-file handling and does not configure HTTP
authentication. Because the root filesystem is the document tree, URL paths
map to filesystem paths. This is confirmed for selected files:

- `GET /etc/inittab` returned the same 89 bytes as the dumped file.
- `GET /bin/remote` returned the same 78,320 bytes as the dumped binary.
- The owner confirmed `/tmp/www/ver.html` returns firmware details and the
  configured SSID/passphrase (redacted in shared evidence).

These results establish broad unauthenticated file reads for the inspected
firmware. They do not prove that every filesystem path is readable: runtime
files, mounts, permissions, symlinks and web-server path handling can affect
individual URLs. The FTP tree is incomplete for `/proc`, `/sys`, device nodes
and runtime mounts.

## Useful read-only targets

Candidate paths follow from the static root and the dumped filesystem. Unless
marked confirmed above, their HTTP behavior has not been requested or verified.

| URL path | Useful for | Status |
| --- | --- | --- |
| `/version`, `/ver.log` | Record Wi-Fi firmware and build identifiers | Present in dump; not separately tested on 8083 |
| `/etc/lighttpd.conf` | Confirm server root, bind address, MIME types and access settings | Present in dump; not separately tested on 8083 |
| `/etc/rc.d/rcS` | Understand startup order, generated status page, services and recovery triggers | Present in dump; not separately tested on 8083 |
| `/5aw/uvc.html`, `/5aw/memu.html` | Inspect the selected-family UI and its control requests | Present in dump; not separately tested on 8083 |
| `/bin/remote`, `/bin/getsetting` | Preserve or compare firmware tools for offline reverse engineering | `/bin/remote` confirmed; `getsetting` not separately tested on 8083 |
| `/tmp/ftp/SDdisk/DCIM/...` | Potentially retrieve camera media over HTTP when the SD mount and exact path exist | Candidate only; media paths are private and untested over HTTP |

The last candidate could provide a simple owner-operated media retrieval path
from a known filename, since the boot script mounts the card at
`/tmp/ftp/SDdisk` and the web server serves from `/`. Do not assume directory
listing or byte-range support. Use the FTP listing to learn exact paths and
limit any future check to a known file on the owner's camera.

For firmware research, the low-risk practical targets are `/version`,
`/ver.log`, `/etc/lighttpd.conf`, `/etc/rc.d/rcS` and model-family HTML. They
can support build identification, web-UI reconstruction and comparisons across
firmware copies without changing camera state. Avoid update, reset, format,
configuration-write and CGI actions during this read-only exploration.

## Do the vendor apps use port 8083?

No `8083` literal was found in the decoded Android APK (DEX, smali, resources or
native library) or in printable strings from the supplied Windows and macOS
executables. The Android APK instead contains a direct preview URL on port
`8084`, uses the binary control protocol, and has FTP defaults for the camera.
The HTML firmware UI uses relative `/cgi-bin/...` actions and direct preview
requests on port `8080`; when opened from the camera's ordinary web UI these
relative paths resolve on its default HTTP port `80`. The Windows and macOS
apps show USB/config-file behavior in the existing reverse-engineering notes.

This is a static reference search, not network tracing. It does not rule out a
port being assembled dynamically or hidden in an uninspected dependency, but
the inspected app code provides no evidence that the vendor applications use
the 8083 filesystem service.
