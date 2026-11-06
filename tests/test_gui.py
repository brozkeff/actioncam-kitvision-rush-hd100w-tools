"""Checks for GUI command isolation and preview lifecycle."""

import subprocess
import threading
import unittest
from pathlib import Path
from unittest import mock

from tools import gui


class GuiTests(unittest.TestCase):
    def test_control_runs_existing_cli_with_bounded_timeout(self) -> None:
        result = subprocess.CompletedProcess([], 0, '{"ok": true}', "")
        with mock.patch.object(gui.subprocess, "run", return_value=result) as run:
            self.assertIs(gui.run_control("192.168.1.2", "record", "start"), result)
        args, kwargs = run.call_args
        self.assertEqual(Path(args[0][1]).name, "control.py")
        self.assertEqual(args[0][2:], ["--host", "192.168.1.2", "record", "start"])
        self.assertEqual(kwargs["timeout"], 60)
        self.assertTrue(kwargs["capture_output"])

    def test_stop_preview_invalidates_late_frames(self) -> None:
        window = gui.CameraWindow.__new__(gui.CameraWindow)
        stop = threading.Event()
        window.preview_stop = stop
        window.preview_generation = 2
        window.preview_status = mock.Mock()
        window.image_label = mock.Mock()
        window.photo = None
        window.stop_preview()
        self.assertTrue(stop.is_set())
        self.assertIsNone(window.preview_stop)
        self.assertEqual(window.preview_generation, 3)

    def test_mode_command_stops_preview_before_dispatch(self) -> None:
        window = gui.CameraWindow.__new__(gui.CameraWindow)
        with (
            mock.patch.object(window, "stop_preview") as stop,
            mock.patch.object(window, "launch") as launch,
        ):
            window.command("mode", "realtime")
        stop.assert_called_once()
        launch.assert_called_once_with(("mode", "realtime"))


if __name__ == "__main__":
    unittest.main()
