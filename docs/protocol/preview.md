# Live preview

## Verified observations

- Live `http://192.168.1.2/uvc.html` returned HTTP 200 and exactly matched
  the 6241-byte saved copy in `tmp/camera/files/uvc.html`.
- The page creates repeated JPEG image requests, not an HTML video stream.
- Each request uses port 8080, path `/?action=snapshot&n=COUNTER`.
- `n` is incremented by JavaScript (`++imageNr`) to vary the URL for caching.
- The next image is requested from imageOnload; two layers avoid flicker.
- Clicking the image toggles request-loop pause. This does not stop recording.
- Page load also POSTs to `/cgi-bin/uvc`, with no request body specified,
  before/alongside snapshot fetching. This is a camera mode action, not a
  harmless status endpoint. The agent fetched source without running its JS.
- Port 8080 was closed in the full TCP scan, then open after the user opened
  preview. The timing supports an on-demand preview service; causation needs
  checking against CGI disassembly.
- A snapshot request returned HTTP 200, image/jpeg, 16566 bytes, JPEG signature.
  Saved image is private and ignored at `tmp/camera/preview-snapshot.jpg`.
- `http://192.168.1.2:8080/?action=stream` also returned HTTP 200 and
  `multipart/x-mixed-replace;boundary=boundarydonotcross`.
- The first multipart headers identified image/jpeg, a frame length of 16076
  bytes and X-Timestamp. Only 256 stream bytes were read before closing.
- Port 8084 remained open alongside 8080. Do not conflate the separate preview
  services or assume both can coexist with recording.

## Application implications

### Android 16 failure reproduced from Linux

The owner reported Android access to the known service ports except 8080,
which returned connection refused. A Linux recheck also found ports 80 and
8084 accepting connections and 8080 refusing them. Status reported
`Mass_Storage`, battery 100%, recording false. The process list contained no
MJPEG streamer, and `/sys/bus/usb/devices` contained only `usb1` and `1-0:1.0`;
the downstream USB camera product path was absent. The existing `/dev/video0`
node alone did not establish that a camera was attached.

One activation POST from Linux timed out after 15 seconds. Captured headers
included HTTP 200 and the CGI messages `set host mode` and `CMDid 0004`;
the preview listener did not start during the observation. This reproduces
the startup failure independently of Android and points to the camera's mode
transition/internal USB state. The precise cause and recovery remain unknown.
Do not treat a successful CGI HTTP status as successful preview activation.

The owner subsequently disconnected and reconnected camera power and confirmed
that Android preview worked. This verifies preview delivery on Moto G85 with
Android 16 after recovery; the cause of the stuck camera state remains unknown.

- Desktop preview can likely consume ordinary MJPEG without the vendor SDK.
- Model preview activation/deactivation explicitly and validate recording
  compatibility before automatically switching modes.
- Do not use image timestamps as proof of the recording camera clock: the
  streaming server runs on the Wi-Fi Linux subsystem.
- Determine capture resolution from JPEG metadata; the page's 512x384 display
  dimensions alone do not establish sensor/output dimensions.

## Verified activation experiment and prototype

- Before activation, diagnostics confirmed TCP 8080 closed.
- Sent one empty-body POST to `http://192.168.1.2/cgi-bin/uvc`, matching
  runuvc() in uvc.html, with that page as Referer. No browser was needed.
- The HTTP call timed out after 12 seconds. Polling then found the listener
  at 13.852 seconds from POST start; this is an observation time, not proof
  of the exact instant it opened.
- Snapshot subsequently returned HTTP 200 and a 16446-byte JPEG.
- Evidence: ignored `tmp/camera/preview-activation.json` and
  `tmp/camera/activated-preview.jpg`.
- Implemented `preview-start` and `snapshot --activate` in tools/rush.py.
- The prototype skips activation when 8080 already listens. Otherwise it sends
  exactly one POST and polls within the startup deadline, tolerating CGI timeout.
- A live prototype capture with preview already active saved a 16378-byte JPEG.
- Unit tests cover existing listener, CGI timeout followed by readiness, and
  startup expiry; snapshot tests cover validation and overwrite protection.
- Activation leaves preview enabled. No automatic USB/mass-storage restoration
  was attempted, and recording/clock operations were not changed.

## Host webcam integration

See [virtual webcam operation](../virtual-webcam.md) for the Python launcher.
Compressed MJPEG output and V4L2 readback at 320x240 were verified.

## Multipart reliability follow-up

Longer runs produced corrupt multipart packets followed by HTTP timeouts.
Repeated snapshots also experienced transient stalls, then resumed. The webcam
launcher now defaults to validated, cache-busted snapshots piped into FFmpeg;
MJPEG V4L2 passthrough remains compressed. A ten-frame consumer test recovered
from two snapshot timeouts while retaining the producer process. See the
webcam guide for transport selection and this host's setup.
