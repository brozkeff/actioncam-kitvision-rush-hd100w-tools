"""Rush camera status, recording and recording-clock control over Wi-Fi."""

import argparse
import datetime as dt
import json
import sys
import time

if __package__:
    from .protocol import Camera
    from .rush import host_address
else:
    from protocol import Camera
    from rush import host_address


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command-line arguments for either interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=host_address, default="192.168.1.2")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("info")
    commands.add_parser("status")
    commands.add_parser("settings")
    clock = commands.add_parser("clock")
    actions = clock.add_subparsers(dest="action", required=True)
    actions.add_parser("get")
    set_clock = actions.add_parser("set")
    values = set_clock.add_mutually_exclusive_group(required=True)
    values.add_argument("--now", action="store_true")
    values.add_argument(
        "--at", type=dt.datetime.fromisoformat, help="ISO local wall time"
    )
    set_clock.add_argument("--dry-run", action="store_true")
    mode = commands.add_parser("mode")
    mode.add_argument("value", choices=("realtime", "storage"))
    record = commands.add_parser("record")
    record.add_argument("action", choices=("start", "stop"))
    return parser.parse_args(argv)


def execute(args: argparse.Namespace) -> dict:
    """Run one control operation and return its structured result."""
    if args.command == "clock" and args.action == "set":
        value = dt.datetime.now().astimezone() if args.now else args.at
        if value.tzinfo is not None:
            value = value.astimezone()
        if not 1970 <= value.year <= 2069:
            raise ValueError("Camera clock year must be 1970–2069")
        if args.dry_run:
            return {"wall_time": value.replace(tzinfo=None).isoformat(), "dry_run": True}
    with Camera(args.host, timeout=15) as camera:
        if args.command == "info":
            info = camera.version()
            camera.authenticate()
            return {**info, **camera.identity()}
        camera.authenticate()
        if args.command == "status":
            result = camera.status()
        elif args.command == "settings":
            result = camera.settings()
        elif args.command == "clock":
            if args.action == "set":
                before = camera.clock()
                camera.set_clock(value)
                readback = camera.clock()
                if abs((readback - value.replace(tzinfo=None)).total_seconds()) > 5:
                    raise ValueError(
                        "Clock acknowledged but readback differs by more than five seconds"
                    )
                result = {
                    "before": before.isoformat(),
                    "readback": readback.isoformat(),
                    "verified": True,
                    "timezone": "local wall time; camera stores no timezone",
                }
            else:
                result = {
                    "wall_time": camera.clock().isoformat(),
                    "timezone": "unspecified",
                }
        elif args.command == "mode":
            status = camera.status()
            if status["recording"]:
                raise ValueError("Stop recording before changing mode")
            camera.mode("Real_Time" if args.value == "realtime" else "Mass_Storage")
            result = camera.status()
        else:
            status = camera.status()
            target = args.action == "start"
            if bool(status["recording"]) == target:
                result = {**status, "changed": False}
            else:
                if target and status["mode"] != "Real_Time":
                    raise ValueError(
                        "Recording requires Real_Time mode; stop webcam and run mode realtime first"
                    )
                camera.record(target)
                after = camera.status()
                deadline = time.monotonic() + 2
                while (
                    bool(after["recording"]) != target
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.25)
                    after = camera.status()
                if bool(after["recording"]) != target:
                    raise ValueError(
                        "Recording command acknowledged but state did not change"
                    )
                result = {**after, "acknowledged": True, "verified": True}
        return result


def main() -> int:
    """Run a control command and report a shell exit status."""
    args = parse_args()
    try:
        print(json.dumps(execute(args)))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(
            f"control: {error}. Writes are not retried automatically; check status before repeating.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
