"""Camera discovery and preview prototypes; control lives in control.py."""

import argparse
import concurrent.futures
import ipaddress
import json
import math
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PORTS = (21, 23, 53, 80, 6667, 8080, 8083, 8084)


def host_address(value: str) -> str:
    """Validate and normalize a camera IPv4 address.

    Args:
        value: Address supplied by the user.

    Returns:
        Canonical dotted-decimal address.
    """
    return str(ipaddress.IPv4Address(value))


def port_open(host: str, port: int, timeout: float) -> bool:
    """Check whether a TCP service accepts connections within a deadline.

    Args:
        host: Camera address.
        port: TCP port to probe.
        timeout: Connection timeout in seconds.

    Returns:
        True when the connection succeeds.
    """
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def enable_preview(
    host: str, timeout: float, startup_timeout: float
) -> dict[str, str | bool]:
    """Start the preview as the vendor page does, allowing the CGI to hang.

    A listening port is used as readiness evidence; it does not guarantee frames.

    Args:
        host: Camera address.
        timeout: Per-operation timeout in seconds.
        startup_timeout: Overall startup budget in seconds.

    Returns:
        Readiness and activation outcome.
    """
    if port_open(host, 8080, min(timeout, 0.5)):
        return {"preview_ready": True, "activation": "already listening"}
    deadline = time.monotonic() + startup_timeout
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        f"http://{host}/cgi-bin/uvc",
        data=b"",
        method="POST",
        headers={"Referer": f"http://{host}/uvc.html"},
    )
    outcome = "HTTP response received"
    try:
        with opener.open(request, timeout=min(timeout, startup_timeout)) as response:
            response.read(65536)
    except TimeoutError:
        outcome = "CGI timed out; activation continued"
    except urllib.error.URLError as error:
        if not isinstance(error.reason, TimeoutError):
            raise
        outcome = "CGI timed out; activation continued"
    while (remaining := deadline - time.monotonic()) > 0:
        if port_open(host, 8080, min(timeout, remaining, 0.5)):
            return {"preview_ready": True, "activation": outcome}
        time.sleep(min(0.25, max(0, deadline - time.monotonic())))
    raise TimeoutError(
        "Preview port 8080 did not open before startup timeout; "
        "activation POST was sent once and camera mode may have changed"
    )


def fetch_snapshot(host: str, timeout: float) -> bytes:
    # Avoid HTTP proxies: this operation always targets the explicit camera IP.
    """Fetch and validate one complete JPEG without using a proxy or cache.

    Args:
        host: Camera address.
        timeout: HTTP timeout in seconds.

    Returns:
        JPEG bytes including the start and end markers.
    """
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        f"http://{host}:8080/?action=snapshot&n={time.time_ns()}",
        headers={"Cache-Control": "no-cache"},
    )
    with opener.open(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("Snapshot exceeds 2 MB limit")
    if content_type != "image/jpeg" or not payload.startswith(b"\xff\xd8"):
        raise ValueError("Camera did not return a JPEG snapshot")
    if not payload.endswith(b"\xff\xd9"):
        raise ValueError("Camera returned an incomplete JPEG")
    return payload


def snapshot(host: str, timeout: float, output: Path) -> dict[str, str | int]:
    """Save a preview frame without replacing an existing file.

    Args:
        host: Camera address.
        timeout: HTTP timeout in seconds.
        output: New destination path.

    Returns:
        Path, byte count and content type.
    """
    payload = fetch_snapshot(host, timeout)
    # Exclusive creation avoids replacing an existing photo or other file.
    with output.open("xb") as destination:
        destination.write(payload)
    return {"path": str(output), "bytes": len(payload), "content_type": "image/jpeg"}


def main() -> int:
    """Run the discovery or preview command and return a shell exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=host_address, default="192.168.1.2")
    parser.add_argument("--timeout", type=float, default=3.0)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect", help="Check known TCP service listeners")
    commands.add_parser("preview-start", help="Activate camera preview mode")
    parser.add_argument("--startup-timeout", type=float, default=20.0)
    photo = commands.add_parser("snapshot", help="Save JPEG from preview")
    photo.add_argument(
        "--activate", action="store_true", help="Activate preview first if needed"
    )
    photo.add_argument("output", type=Path)
    args = parser.parse_args()
    if not all(
        math.isfinite(t) and t > 0 for t in (args.timeout, args.startup_timeout)
    ):
        parser.error("timeouts must be finite and positive")
    try:
        if args.command == "inspect":
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(
                    pool.map(
                        lambda port: port_open(args.host, port, args.timeout), PORTS
                    )
                )
            print(json.dumps({"host": args.host, "ports": dict(zip(PORTS, results))}))
            return 0 if any(results) else 1
        if args.command == "preview-start":
            print(
                json.dumps(
                    enable_preview(args.host, args.timeout, args.startup_timeout)
                )
            )
            return 0
        if args.output.exists():
            raise FileExistsError(f"Output already exists: {args.output}")
        if args.activate:
            activation = enable_preview(args.host, args.timeout, args.startup_timeout)
            print(json.dumps(activation), file=sys.stderr)
        print(json.dumps(snapshot(args.host, args.timeout, args.output)))
        return 0
    except (OSError, ValueError, urllib.error.URLError) as error:
        print(f"rush: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
