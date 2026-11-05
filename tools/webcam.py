"""Activate Rush preview and publish a Linux V4L2 webcam via FFmpeg."""

import argparse
import json
import math
import os
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

if __package__:
    from .rush import enable_preview, fetch_snapshot, host_address
else:
    from rush import enable_preview, fetch_snapshot, host_address


def privileged(arguments: list[str]) -> list[str]:
    """Prefix an administrative command with sudo when needed.

    Args:
        arguments: Command and arguments.

    Returns:
        Command suitable for execution.
    """
    return arguments if os.geteuid() == 0 else ["sudo", "--", *arguments]


def allocate_camera(label: str) -> Path:
    """Create a uniquely allocated loopback without reloading an existing module.

    Args:
        label: User-visible device name.

    Returns:
        Newly allocated video device path.
    """
    ctl = shutil.which("v4l2loopback-ctl")
    if not ctl:
        raise RuntimeError(
            "Install a current v4l2loopback driver and v4l2loopback-ctl with "
            "dynamic 'add/delete' support. See docs/virtual-webcam.md."
        )
    if not Path("/dev/v4l2loopback").exists():
        if not Path("/sys/module/v4l2loopback").exists():
            subprocess.run(
                privileged(["modprobe", "v4l2loopback", "devices=0"]), check=True
            )
        if not Path("/dev/v4l2loopback").exists():
            raise RuntimeError(
                "Loaded v4l2loopback lacks /dev/v4l2loopback dynamic control. "
                "Upgrade the driver, or explicitly use --device /dev/videoN. "
                "Existing devices were not reloaded or removed."
            )
    result = subprocess.run(
        privileged([ctl, "add", "-n", label, "-x", "1"]),
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"(?m)^(/dev/video[0-9]+)\s*$", result.stdout)
    if not match:
        raise RuntimeError(f"Unrecognized allocation reply: {result.stdout!r}")
    return Path(match[1])


def validate_camera(device: Path) -> None:
    """Ensure an existing writable video device belongs to v4l2loopback.

    Args:
        device: Video device path to inspect.
    """
    if not re.fullmatch(r"/dev/video[0-9]+", str(device)):
        raise ValueError("Device must be /dev/videoN")
    if not stat.S_ISCHR(device.stat().st_mode):
        raise ValueError(f"Not a video character device: {device}")
    result = subprocess.run(
        ["v4l2-ctl", "--device", str(device), "--info"],
        check=True,
        capture_output=True,
        text=True,
    )
    if not re.search(r"Driver name\s*:\s*v4l2 loopback", result.stdout):
        raise ValueError(f"Refusing non-loopback camera: {device}")
    if not os.access(device, os.W_OK):
        raise PermissionError(
            f"No write access to {device}; check video group/udev ACLs"
        )


def ffmpeg_command(
    host: str, device: Path, output_format: str, source: str = "stream", fps: float = 10
) -> list[str]:
    """Build the FFmpeg command for JPEG passthrough or YUYV output.

    Args:
        host: Camera address.
        device: Destination loopback device.
        output_format: Either mjpeg or yuyv.
        source: Snapshot pipe or direct multipart stream.
        fps: Snapshot input frame rate.

    Returns:
        Argument vector for FFmpeg.
    """
    command = ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-nostdin"]
    if source == "snapshots":
        command += [
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "-framerate",
            str(fps),
            "-probesize",
            "32768",
            "-analyzeduration",
            "0",
            "-threads",
            "1",
            "-i",
            "pipe:0",
        ]
    else:
        command += [
            "-rw_timeout",
            "5000000",
            "-f",
            "mpjpeg",
            "-i",
            f"http://{host}:8080/?action=stream",
        ]
    command += ["-map", "0:v:0", "-an"]
    if output_format == "mjpeg":
        command += ["-c:v", "copy"]
    else:
        command += ["-c:v", "rawvideo", "-pix_fmt", "yuyv422", "-threads", "1"]
    return command + ["-f", "v4l2", str(device)]


def pump_snapshots(
    process: subprocess.Popen[bytes], host: str, fps: float, deadline: float | None
) -> None:
    """Feed complete JPEGs to FFmpeg with bounded retries and pipe backpressure.

    Args:
        process: FFmpeg process with piped standard input.
        host: Camera address.
        fps: Maximum snapshot rate.
        deadline: Optional monotonic deadline for the producer.
    """
    if process.stdin is None:
        raise RuntimeError("Snapshot producer needs an input pipe")
    fd = process.stdin.fileno()
    os.set_blocking(fd, False)
    frames = 0
    failures = 0
    while deadline is None or time.monotonic() < deadline:
        started = time.monotonic()
        timeout = 3.0 if deadline is None else min(3.0, deadline - started)
        if timeout <= 0:
            return
        try:
            payload = memoryview(fetch_snapshot(host, timeout))
            failures = 0
        except (OSError, ValueError) as error:
            failures += 1
            if failures > 3:
                raise
            print(
                f"webcam: snapshot interrupted ({failures}/3): {error}", file=sys.stderr
            )
            time.sleep(0.25)
            continue
        jpeg_bytes = len(payload)
        write_deadline = time.monotonic() + 5
        if deadline is not None:
            write_deadline = min(write_deadline, deadline)
        while payload:
            if process.poll() is not None:
                raise RuntimeError(f"FFmpeg exited with code {process.returncode}")
            remaining = write_deadline - time.monotonic()
            if remaining <= 0:
                if deadline is not None and time.monotonic() >= deadline:
                    return
                raise TimeoutError("FFmpeg stopped accepting JPEG frames")
            _, writable, _ = select.select([], [fd], [], min(remaining, 0.5))
            if writable:
                try:
                    written = os.write(fd, payload)
                except BlockingIOError:
                    continue
                if written == 0:
                    raise BrokenPipeError("FFmpeg input closed")
                payload = payload[written:]
        frames += 1
        if frames == 1:
            print(
                json.dumps(
                    {
                        "event": "first_jpeg_submitted",
                        "bytes": jpeg_bytes,
                        "source": "snapshots",
                    }
                ),
                flush=True,
            )
        wait = max(0.0, 1 / fps - (time.monotonic() - started))
        if deadline is not None:
            wait = min(wait, max(0.0, deadline - time.monotonic()))
        time.sleep(wait)


def stop_process(process: subprocess.Popen[bytes]) -> None:
    """Stop FFmpeg gracefully, then kill it if it fails to exit.

    Args:
        process: Producer process owned by this launcher.
    """
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    """Launch and supervise a virtual webcam; return a shell exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=host_address, default="192.168.1.2")
    parser.add_argument(
        "--device", type=Path, help="Use an existing loopback explicitly"
    )
    parser.add_argument("--label", default="Rush HD100W")
    parser.add_argument("--format", choices=("mjpeg", "yuyv"), default="mjpeg")
    parser.add_argument(
        "--duration", type=float, help="Stop after this many wall-clock seconds"
    )
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--source", choices=("snapshots", "stream"), default="snapshots"
    )
    parser.add_argument("--fps", type=float, default=10, help="Maximum snapshot rate")
    args = parser.parse_args()
    if not math.isfinite(args.fps) or not 0 < args.fps <= 30:
        parser.error("fps must be finite and between 0 and 30")
    if args.retries < 0 or (
        args.duration is not None
        and (not math.isfinite(args.duration) or args.duration <= 0)
    ):
        parser.error("duration must be finite/positive and retries nonnegative")
    if not args.label or len(args.label.encode()) > 31:
        parser.error("label must be 1–31 bytes")
    for executable in ("ffmpeg", "v4l2-ctl"):
        if not shutil.which(executable):
            parser.error(f"Missing executable: {executable}")
    device = args.device
    owned = False
    exit_code = 0

    def interrupted(_signum: int, _frame: object) -> None:
        """Translate termination into the normal cleanup path.

        Args:
            _signum: Received signal number.
            _frame: Interrupted Python frame.
        """
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        if device is None:
            device = allocate_camera(args.label)
            owned = True
        # Allow udev to create the node and apply desktop ACLs.
        deadline = time.monotonic() + 3
        while (
            not device.exists() or not os.access(device, os.W_OK)
        ) and time.monotonic() < deadline:
            time.sleep(0.1)
        validate_camera(device)
        environment = os.environ.copy()
        for key in tuple(environment):
            if key.lower() in ("http_proxy", "https_proxy", "all_proxy"):
                environment.pop(key)
        deadline = None if args.duration is None else time.monotonic() + args.duration
        for attempt in range(args.retries + 1):
            try:
                enable_preview(args.host, 3, 20)
            except OSError as error:
                if attempt == args.retries:
                    raise
                print(f"webcam: camera unavailable: {error}; retrying", file=sys.stderr)
                time.sleep(1)
                continue
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                break
            with subprocess.Popen(
                ffmpeg_command(args.host, device, args.format, args.source, args.fps),
                stdin=subprocess.PIPE
                if args.source == "snapshots"
                else subprocess.DEVNULL,
                bufsize=0,
                env=environment,
                start_new_session=True,
            ) as process:
                print(
                    json.dumps(
                        {
                            "device": str(device),
                            "format": args.format,
                            "event": "producer_started",
                            "attempt": attempt + 1,
                        }
                    ),
                    flush=True,
                )
                try:
                    if args.source == "snapshots":
                        pump_snapshots(process, args.host, args.fps, deadline)
                        break
                    code = process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    break
                except (OSError, ValueError, RuntimeError) as error:
                    print(f"webcam: frame transport failed: {error}", file=sys.stderr)
                    code = process.poll() or -1
                finally:
                    stop_process(process)
            if attempt == args.retries:
                raise RuntimeError(
                    f"Stream ended after {attempt + 1} attempts (FFmpeg exit {code})"
                )
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"webcam: {error}", file=sys.stderr)
        exit_code = 1
    finally:
        if owned and device is not None:
            try:
                subprocess.run(
                    privileged(["v4l2loopback-ctl", "delete", str(device)]), check=True
                )
            except (OSError, subprocess.SubprocessError) as error:
                print(
                    f"webcam: cleanup failed for {device}: {error}; close camera consumers and retry deletion",
                    file=sys.stderr,
                )
                exit_code = 1
        signal.signal(signal.SIGTERM, previous)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
