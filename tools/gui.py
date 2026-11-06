"""Experimental Tkinter controller for the Rush HD100W camera."""

import argparse
import io
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk
from typing import Any

from PIL import Image, ImageTk

if __package__:
    from .rush import enable_preview, fetch_snapshot, host_address
else:
    from rush import enable_preview, fetch_snapshot, host_address

TOOLS = Path(__file__).resolve().parent


def run_control(host: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the existing CLI with a bounded wait and capture its output.

    Args:
        host: Validated camera IPv4 address.
        *arguments: Control CLI subcommand and arguments.

    Returns:
        Completed command including stdout, stderr and exit status.
    """
    return subprocess.run(
        [sys.executable, str(TOOLS / "control.py"), "--host", host, *arguments],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


class CameraWindow:
    """Coordinate a Tk interface and background camera operations."""

    def __init__(self, root: tk.Tk, host: str) -> None:
        """Build the window and begin periodic status polling.

        Args:
            root: Tk root owned by the main thread.
            host: Validated camera address.
        """
        self.root = root
        self.host = host
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.frames: queue.Queue[tuple[int, Image.Image]] = queue.Queue(maxsize=1)
        self.control_lock = threading.Lock()
        self.control_busy = False
        self.preview_stop: threading.Event | None = None
        self.preview_generation = 0
        self.photo: ImageTk.PhotoImage | None = None
        self.closed = False
        self.status = tk.StringVar(value="Connecting…")
        self.clock = tk.StringVar(value="Camera time: unknown")
        self.preview_status = tk.StringVar(value="Preview stopped")
        root.title(f"Rush HD100W — {host}")
        root.minsize(640, 600)
        root.protocol("WM_DELETE_WINDOW", self.close)
        outer = ttk.Frame(root, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, textvariable=self.status, wraplength=760).pack(anchor="w")
        ttk.Label(outer, textvariable=self.clock).pack(anchor="w", pady=(2, 8))
        controls = ttk.Frame(outer)
        controls.pack(fill="x")
        for label, command in (
            ("Refresh", self.refresh),
            ("Camera info", lambda: self.command("info")),
            ("Settings", lambda: self.command("settings")),
            ("Set time to now", lambda: self.command("clock", "set", "--now")),
        ):
            ttk.Button(controls, text=label, command=command).pack(side="left", padx=2)
        modes = ttk.Frame(outer)
        modes.pack(fill="x", pady=6)
        for label, arguments in (
            ("Real-time mode", ("mode", "realtime")),
            ("Storage mode", ("mode", "storage")),
            ("Start recording", ("record", "start")),
            ("Stop recording", ("record", "stop")),
        ):
            ttk.Button(
                modes, text=label, command=lambda a=arguments: self.command(*a)
            ).pack(side="left", padx=2)
        ttk.Label(
            outer,
            text="Mode switching and recording are experimental and may be rejected.",
        ).pack(anchor="w")
        preview_controls = ttk.Frame(outer)
        preview_controls.pack(fill="x", pady=6)
        ttk.Button(
            preview_controls, text="Start preview", command=self.start_preview
        ).pack(side="left", padx=2)
        ttk.Button(
            preview_controls, text="Stop preview", command=self.stop_preview
        ).pack(side="left", padx=2)
        ttk.Label(preview_controls, textvariable=self.preview_status).pack(
            side="left", padx=8
        )
        self.image_label = ttk.Label(outer, text="No preview", anchor="center")
        self.image_label.pack(fill="both", expand=True, pady=4)
        ttk.Label(outer, text="Command output").pack(anchor="w")
        self.output = scrolledtext.ScrolledText(
            outer, height=9, state="disabled", wrap="word"
        )
        self.output.pack(fill="both", expand=True)
        self.root.after(100, self.drain_events)
        self.root.after(100, self.poll_status)

    def log(self, message: str) -> None:
        """Append a command result to the output box on the Tk thread."""
        self.output.configure(state="normal")
        self.output.insert("end", message.rstrip() + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def launch(self, arguments: tuple[str, ...], *, poll: bool = False) -> None:
        """Run one control operation without blocking Tk or overlapping another.

        Args:
            arguments: Control CLI arguments.
            poll: Whether this is the quiet periodic status and clock query.
        """
        if self.control_busy:
            if not poll:
                self.log(
                    "A camera command is still running; try again when it finishes."
                )
            return
        self.control_busy = True
        host = self.host

        def worker() -> None:
            try:
                with self.control_lock:
                    if poll:
                        status = run_control(host, "status")
                        clock = (
                            run_control(host, "clock", "get")
                            if status.returncode == 0
                            else None
                        )
                        self.events.put(("poll", (status, clock)))
                    else:
                        result = run_control(host, *arguments)
                        self.events.put(("command", (arguments, result)))
            except (OSError, subprocess.SubprocessError) as error:
                self.events.put(("failure", (poll, str(error))))
            finally:
                self.events.put(("idle", None))

        threading.Thread(target=worker, daemon=True).start()

    def command(self, *arguments: str) -> None:
        """Start a requested CLI command and stop preview before mode changes."""
        if arguments[0] in ("mode", "record"):
            self.stop_preview()
        self.launch(arguments)

    def refresh(self) -> None:
        """Request an immediate status and camera clock refresh."""
        self.launch((), poll=True)

    def poll_status(self) -> None:
        """Schedule regular status refreshes while the window remains open."""
        if not self.closed:
            self.refresh()
            self.root.after(5000, self.poll_status)

    def start_preview(self) -> None:
        """Start one JPEG polling worker, activating preview only on request."""
        if self.preview_stop is not None:
            return
        stop = threading.Event()
        self.preview_stop = stop
        self.preview_generation += 1
        generation = self.preview_generation
        self.preview_status.set("Starting preview…")

        def worker() -> None:
            try:
                with self.control_lock:
                    if stop.is_set():
                        return
                    result = enable_preview(self.host, 3, 20)
                if stop.is_set():
                    return
                self.events.put(("preview_started", (generation, result)))
                failures = 0
                while not stop.is_set():
                    try:
                        with Image.open(
                            io.BytesIO(fetch_snapshot(self.host, 3))
                        ) as image:
                            image.load()
                            frame = image.copy()
                        failures = 0
                    except OSError, ValueError:
                        failures += 1
                        if failures > 3:
                            raise
                        stop.wait(0.25)
                        continue
                    frame.thumbnail((640, 480))
                    if self.frames.full():
                        try:
                            self.frames.get_nowait()
                        except queue.Empty:
                            pass
                    try:
                        self.frames.put_nowait((generation, frame))
                    except queue.Full:
                        pass
                    stop.wait(0.2)
            except (OSError, ValueError) as error:
                self.events.put(("preview_error", (generation, str(error))))

        threading.Thread(target=worker, daemon=True).start()

    def stop_preview(self) -> None:
        """Stop displaying frames and invalidate results from an older worker."""
        if self.preview_stop is not None:
            self.preview_stop.set()
            self.preview_stop = None
            self.preview_generation += 1
        self.preview_status.set("Preview stopped")
        self.photo = None
        self.image_label.configure(image="", text="No preview")

    def drain_events(self) -> None:
        """Apply background results to widgets exclusively on the Tk thread."""
        import json

        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "idle":
                self.control_busy = False
            elif kind == "failure":
                poll, error = value
                if poll:
                    self.status.set(f"Camera unavailable: {error}")
                    self.clock.set("Camera time: unknown")
                else:
                    self.log(f"Command failed: {error}")
            elif kind == "poll":
                status, clock = value
                if status.returncode:
                    self.status.set(
                        "Camera unavailable: "
                        + (status.stderr.strip() or "no response")
                    )
                    self.clock.set("Camera time: unknown")
                else:
                    try:
                        data = json.loads(status.stdout)
                        self.status.set(
                            f"Connected — mode: {data['mode']} | battery: {data['battery_percent']}% | "
                            f"recording: {'yes' if data['recording'] else 'no'}"
                        )
                        if clock is not None and clock.returncode == 0:
                            self.clock.set(
                                "Camera time: " + json.loads(clock.stdout)["wall_time"]
                            )
                        else:
                            self.clock.set("Camera time: unavailable")
                    except (ValueError, KeyError, TypeError) as error:
                        self.status.set(f"Invalid camera response: {error}")
                        self.clock.set("Camera time: unknown")
            elif kind == "command":
                arguments, result = value
                self.log(
                    f"$ control {' '.join(arguments)}\n{result.stdout}{result.stderr}".rstrip()
                )
            elif kind == "preview_started":
                generation, result = value
                if generation == self.preview_generation:
                    self.preview_status.set("Preview active")
                    self.log(f"Preview: {result['activation']}")
            elif kind == "preview_error":
                generation, error = value
                if generation == self.preview_generation:
                    self.stop_preview()
                    self.preview_status.set("Preview failed")
                    self.log(f"Preview failed: {error}")
        try:
            generation, frame = self.frames.get_nowait()
            if generation == self.preview_generation and self.preview_stop is not None:
                self.photo = ImageTk.PhotoImage(frame)
                self.image_label.configure(image=self.photo, text="")
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(100, self.drain_events)

    def close(self) -> None:
        """Stop background preview and close the window without blocking Tk."""
        self.closed = True
        self.stop_preview()
        self.root.destroy()


def main() -> int:
    """Parse options and start the graphical application.

    Returns:
        Zero after the window closes, or one if Tk cannot start.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=host_address, default="192.168.1.2")
    args = parser.parse_args()
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"gui: Cannot open a graphical display: {error}", file=sys.stderr)
        return 1
    CameraWindow(root, args.host)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
