# Generated status page contains Wi-Fi credentials

## Verified exposure

Review of the private firmware copy in ignored `tmp/camera/rootfs/` found:

- The active `/etc/rc.d/rcS` reads `/dev/nvram` into a temporary file.
- It extracts `AP_SSID` and `PSK_KEY` and writes each value to
  `/tmp/www/ver.html` using `sed`.
- `/etc/lighttpd.conf` sets `server.document-root = "/"`, binds to
  `192.168.1.2`, and listens on port `8083` without an authentication rule.
- The dynamic page is therefore expected to be reachable at
  `http://192.168.1.2:8083/tmp/www/ver.html` while that boot script and server
  configuration are active.

The owner opened `http://192.168.1.2:8083/tmp/www/ver.html` and confirmed the
page displays the firmware version, configured SSID and passphrase, release
time, card update filename and realtime support text. The owner redacted both
credentials in the shared output. This verifies unauthenticated disclosure for
the inspected camera and firmware; it does not establish behavior on other
models or revisions.

## Impact

Anyone able to reach the camera's web service may be able to read the Wi-Fi
network name and passphrase from the status page. If the camera is using its
own hotspot, that can disclose the credential protecting the same local
network. Avoid sharing the generated page or raw NVRAM dump. This finding is
specific to the inspected Rush HD100W firmware and is not evidence about other
camera models or revisions.
