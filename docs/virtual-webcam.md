# Linux virtual webcam

## Pipeline and requirements

The Python launcher activates preview and supervises FFmpeg. By default Python
fetches complete JPEG snapshots and pipes them to FFmpeg, which writes V4L2
frames. `--source stream` selects direct multipart HTTP input. The existing
v4l2loopback kernel driver creates the webcam applications see.
There is no new kernel driver and no Python video decoder in this pipeline.

Requirements:

- Linux, Python 3.15 and uv.
- FFmpeg and v4l2-ctl (`v4l-utils` on Debian/Ubuntu).
- v4l2loopback kernel module matching the running kernel.
- For automatic device allocation: a recent v4l2loopback module exposing
  `/dev/v4l2loopback` and matching v4l2loopback-ctl with add/delete support.
- Write access to the resulting video device via desktop udev ACLs or the
  video group; permission to allocate/delete devices, usually via sudo.

Consult [upstream v4l2loopback installation and dynamic device guidance][driver].
Distribution package versions vary: having a loopback webcam does not prove
that dynamic allocation is available. Secure Boot may require a signed module.
The launcher does not install packages, replace drivers, unload existing
modules or change persistent boot configuration.

## Launch

```sh
uv sync
uv run python tools/webcam.py
```

Default behavior:

1. Verify dependencies, request an unused device number from v4l2loopback-ctl,
   and label the new webcam `Rush HD100W` with exclusive capture/output caps.
2. Wait briefly for device creation/ACLs and verify the V4L2 driver identity.
3. Activate preview if 8080 is closed; tolerate the known CGI response timeout.
4. Fetch JPEGs at up to 10 fps, feed FFmpeg using image2pipe and copy MJPEG
   to V4L2; print producer and first-frame submission events as JSON.
5. Retry stream termination up to three times, without allocating new devices.
6. On Ctrl+C, SIGTERM, duration expiry or error, stop the producer and remove
   only the device this invocation allocated. Leave preview enabled on camera.

The producer_started event means FFmpeg was spawned, not that a consumer has
already verified the first frame. Open the named camera in your application
once the producer is running. There is no microphone/audio stream.

Only modprobe (if the driver was not loaded) and device add/delete use sudo;
normal video transport runs as your user. The terminal may ask for a password.
Do not run the whole uv environment as root. Multiple invocations request
separate devices, but their shared physical camera and modes can still conflict.

If automatic allocation is unavailable, the launcher explains the missing
support rather than hijacking an existing device. After configuring an unused
loopback through your distribution, opt in explicitly:

```sh
uv run python tools/webcam.py --device /dev/video0
```

Replace video0 with your verified loopback device. Explicit devices are
validated as v4l2loopback and never deleted. Stop other writers first. The tool
cannot guarantee that an explicitly selected device is unused by another app.

## Formats and runtime controls

```sh
uv run python tools/webcam.py --format yuyv
uv run python tools/webcam.py --duration 60 --retries 2
uv run python tools/webcam.py --host 192.168.1.2 --label 'Rush camera'
```

MJPEG is the default: compressed JPEG frames pass through without re-encoding.
YUYV decodes to raw yuyv422 for applications that reject compressed webcams.
It costs more CPU than compressed passthrough.
Exclusive capabilities improve compatibility with browser camera enumeration;
individual applications still require testing. A virtual V4L2 device is not
literally a USB device, but is selected through normal Linux webcam interfaces.

The duration budget begins before preview activation. HTTP reads time out
rather than hanging forever; retries are bounded. A power-off or Wi-Fi loss
may leave a last image visible to consumers until the producer exits/restarts.
Close consumers before cleanup. If the kernel reports the owned device busy,
the launcher prints the device path and cleanup failure rather than unloading
all loopbacks. After closing consumers, remove that device with:

```sh
sudo v4l2loopback-ctl delete /dev/videoN
```

SIGKILL or host crashes cannot run Python cleanup; the same manual deletion may
be needed. No automatic service, autostart or persistent module changes are made.

## Verified results and limitations

- Host already provided an unused legacy loopback as video0.
- MJPEG output from camera HTTP to that loopback succeeded using codec copy.
- A separate FFmpeg V4L2 consumer decoded five frames at 320x240.
- The launcher ran with explicit video0 and a 12-second duration, then exited
  successfully. A coordinated launcher/consumer run also decoded five frames
  and both processes exited zero after SIGTERM cleanup.
  Automatic allocation needs newer host support and remains
  unverified on real hardware; mocked tests cover its lifecycle.
- FFmpeg estimated timing (25 fps input, 30 fps consumer) is not a measured
  physical capture rate. Some readback timestamps repeated.
- Consumer tests need a running producer; otherwise V4L2 reads can wait.
- Simultaneous SD recording, browser compatibility and automatic-mode runtime
  ACL behavior remain hardware acceptance tasks.

[driver]: https://github.com/v4l2loopback/v4l2loopback

## This computer: legacy loopback and unreliable multipart stream

Use the existing virtual camera, not the laptop's real webcam:

```sh
uv run python tools/webcam.py --device /dev/video0 --fps 5
```

Close the camera's browser preview tab and other producers while using this
command. The physical laptop camera video1 is deliberately rejected. The bare
command needs newer dynamic-allocation support, which is independent of the
camera HTTP timeout problem; no driver upgrade is needed for explicit video0.

The old multipart endpoint sometimes returns corrupt/incomplete packets and
stalls. Snapshots also occasionally stall, but the new default retries up to
three consecutive failed JPEG fetches while retaining the FFmpeg process.
A fourth consecutive failure restarts the transport within the outer retry
budget. Reject incomplete JPEGs, preserve backpressure and bound write waits.
There may still be a frozen image during camera stalls; this is not a guarantee
of continuous real-time delivery.

A coordinated default-source MJPEG test delivered ten decoded V4L2 frames,
including recovery from two HTTP timeouts, and exited cleanly. The original
multipart source remains available for comparison:

```sh
uv run python tools/webcam.py --device /dev/video0 --source stream
```

For browser compatibility, try `--format yuyv`. This host's initial video0
advertised both capture and output capabilities. If a browser refuses to list
it, stop the launcher and close ALL loopback consumers/producers first, then
reload the existing driver with exclusive capabilities:

```sh
sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback devices=1 video_nr=0 exclusive_caps=1 \
  card_label='Rush HD100W'
uv run python tools/webcam.py --device /dev/video0 --format yuyv --fps 5
```

These administrator commands are manual setup instructions, not actions taken
by the launcher or this session. Unloading affects all existing loopback devices;
do not do it while other virtual webcams are in use. If unload reports busy,
close the remaining consumers rather than force removal. Exclusive mode exposes
capture capabilities after a producer attaches; start the launcher before
selecting the webcam in a browser.

## Raw compatibility verification

After limiting the JPEG input decoder to one thread to avoid initial buffering,
a separate consumer decoded three YUYV frames at 320x240. Producer and consumer
both exited zero. For this host, `--device /dev/video0 --format yuyv --fps 5`
is the verified compatibility command; dynamic allocation remains unavailable.
