"""Record on the camera, then copy the new MOV to a local file."""

import argparse
import datetime as dt
import ftplib
import os
import re
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

if __package__:
    from .protocol import Camera
    from .rush import host_address
else:
    from protocol import Camera
    from rush import host_address

CARD = "/tmp/ftp/SDdisk/DCIM"


def videos(host: str) -> set[str]:
    """List camera MOV paths; failure to access DCIM is not an empty card."""
    with ftplib.FTP() as ftp:
        ftp.connect(host, 21, timeout=10)
        ftp.login("ap71", "")
        ftp.cwd(CARD)
        result = set()
        for directory in ftp.nlst():
            name = directory.rsplit("/", 1)[-1]
            if not re.fullmatch(r"[0-9]{3}[A-Za-z0-9_]+", name):
                continue
            ftp.cwd(name)
            for item in ftp.nlst():
                filename = item.rsplit("/", 1)[-1]
                if re.fullmatch(r"[A-Za-z0-9_.-]+\.MOV", filename, re.IGNORECASE):
                    result.add(f"{name}/{filename}")
            ftp.cwd(CARD)
        return result


def camera_status(host: str) -> dict:
    with Camera(host, timeout=15) as camera:
        camera.authenticate()
        return camera.status()


def change_mode(host: str, mode: str) -> None:
    with Camera(host, timeout=15) as camera:
        camera.authenticate()
        status = camera.status()
        if status["recording"]:
            raise RuntimeError("Camera is recording; refusing to change mode")
        if status["mode"] != mode:
            camera.mode(mode)
        if camera.status()["mode"] != mode:
            raise RuntimeError(f"Camera did not enter {mode}")


def record_command(host: str, start: bool) -> None:
    with Camera(host, timeout=15) as camera:
        camera.authenticate()
        camera.record(start)
    if bool(camera_status(host)["recording"]) != start:
        raise RuntimeError("Recording state did not match the requested operation")


def download(host: str, remote: str, destination: Path) -> None:
    """Download to a temporary sibling and publish only a complete new file."""
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp:
            temp_name = temp.name
            with ftplib.FTP() as ftp:
                ftp.connect(host, 21, timeout=30)
                ftp.login("ap71", "")
                ftp.cwd(CARD)
                ftp.retrbinary(f"RETR {remote}", temp.write)
        os.link(temp_name, destination)
    finally:
        if temp_name is not None:
            os.unlink(temp_name)


def capture(
    host: str,
    destination: Path,
    wait: Callable[[], object],
    notify: Callable[[str], None] = print,
) -> str:
    """Perform one recording, preserving camera files and refusing ambiguous matches."""
    if destination.exists():
        raise FileExistsError(f"Destination exists: {destination}")
    if not destination.parent.is_dir():
        raise FileNotFoundError(
            f"Destination directory does not exist: {destination.parent}"
        )
    status = camera_status(host)
    if status["recording"]:
        raise RuntimeError(
            "Camera is already recording; cannot identify its output safely"
        )
    if status["mode"] != "Mass_Storage":
        change_mode(host, "Mass_Storage")
    before = videos(host)
    change_mode(host, "Real_Time")
    try:
        record_command(host, True)
    except (OSError, ValueError, RuntimeError) as error:
        raise RuntimeError(
            f"Start failed; recording state may have changed. Check camera status: {error}"
        ) from error
    notify("Recording started. Stop recording to save the video.")
    try:
        wait()
    finally:
        try:
            record_command(host, False)
        except (OSError, ValueError, RuntimeError) as error:
            try:
                stopped = not camera_status(host)["recording"]
            except OSError, ValueError, RuntimeError:
                stopped = False
            if not stopped:
                raise RuntimeError(
                    f"Stop could not be verified; check camera status: {error}"
                ) from error
            notify(f"Stop reply failed, but fresh status reports stopped: {error}")
    change_mode(host, "Mass_Storage")
    deadline = time.monotonic() + 20
    while True:
        try:
            new = videos(host) - before
            if new:
                break
        except OSError, ftplib.Error:
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError("No new video found; check the camera card manually")
        time.sleep(1)
    if len(new) != 1:
        raise RuntimeError(
            f"Found {len(new)} new videos; choose the correct file on the camera manually"
        )
    remote = new.pop()
    download(host, remote, destination)
    return remote


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=host_address, default="192.168.1.2")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Local MOV path (default: ./rush-YYYYMMDD-HHMMSS.mov)",
    )
    args = parser.parse_args()
    destination = args.output or Path(f"rush-{dt.datetime.now():%Y%m%d-%H%M%S}.mov")
    try:
        remote = capture(args.host, destination, lambda: input("Press Enter to stop: "))
        print(f"Saved {remote} to {destination}")
        return 0
    except (OSError, ValueError, RuntimeError, ftplib.Error, EOFError) as error:
        print(f"record: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
