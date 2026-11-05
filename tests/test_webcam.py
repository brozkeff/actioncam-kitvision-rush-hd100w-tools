"""Webcam allocation, command construction and cleanup without kernel access."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools import webcam


class WebcamTests(unittest.TestCase):
    def test_mjpeg_copies_frames_and_yuyv_decodes(self) -> None:
        copy = webcam.ffmpeg_command("192.168.1.2", Path("/dev/video7"), "mjpeg")
        raw = webcam.ffmpeg_command("192.168.1.2", Path("/dev/video7"), "yuyv")
        self.assertIn("copy", copy)
        self.assertNotIn("rawvideo", copy)
        self.assertIn("yuyv422", raw)
        self.assertEqual(copy[-3:], ["-f", "v4l2", "/dev/video7"])
        self.assertIn("http://192.168.1.2:8080/?action=stream", copy)

    def test_snapshot_input_uses_jpeg_pipe(self) -> None:
        command = webcam.ffmpeg_command(
            "192.168.1.2", Path("/dev/video7"), "mjpeg", "snapshots", 5
        )
        self.assertIn("image2pipe", command)
        self.assertIn("pipe:0", command)
        self.assertNotIn("mpjpeg", command)

    def test_snapshot_pump_writes_complete_frame_with_backpressure(self) -> None:
        process = MagicMock()
        process.stdin.fileno.return_value = 7
        process.poll.return_value = None
        frame = b"\xff\xd8test\xff\xd9"
        with (
            patch("tools.webcam.fetch_snapshot", return_value=frame),
            patch("tools.webcam.os.set_blocking"),
            patch("tools.webcam.select.select", return_value=([], [7], [])),
            patch("tools.webcam.os.write", side_effect=[4, 4]) as write,
            patch("tools.webcam.time.monotonic", side_effect=[0, 0, 0, 0, 0, 1, 1, 1]),
            patch("tools.webcam.time.sleep"),
        ):
            webcam.pump_snapshots(process, "192.168.1.2", 5, 1)
            self.assertEqual(write.call_count, 2)
            self.assertEqual(bytes(write.call_args_list[0].args[1]), frame)
            self.assertEqual(bytes(write.call_args_list[1].args[1]), frame[4:])

    def test_allocator_requests_free_number_and_exclusive_caps(self) -> None:
        with (
            patch(
                "tools.webcam.shutil.which", return_value="/usr/bin/v4l2loopback-ctl"
            ),
            patch("tools.webcam.os.geteuid", return_value=0),
            patch("tools.webcam.Path.exists", return_value=True),
            patch("tools.webcam.subprocess.run") as run,
        ):
            run.return_value.stdout = "/dev/video7\n"
            self.assertEqual(webcam.allocate_camera("Rush"), Path("/dev/video7"))
            self.assertEqual(
                run.call_args.args[0],
                ["/usr/bin/v4l2loopback-ctl", "add", "-n", "Rush", "-x", "1"],
            )

    def test_missing_control_interface_never_reloads_module(self) -> None:
        with (
            patch(
                "tools.webcam.shutil.which", return_value="/usr/bin/v4l2loopback-ctl"
            ),
            patch("tools.webcam.Path.exists", side_effect=[False, True, False]),
            patch("tools.webcam.subprocess.run") as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "Existing devices"):
                webcam.allocate_camera("Rush")
            run.assert_not_called()

    def test_owned_device_cleanup_and_explicit_device_preservation(self) -> None:
        for owned in (True, False):
            with (
                self.subTest(owned=owned),
                patch(
                    "tools.webcam.sys.argv",
                    ["webcam", "--source", "stream"]
                    + ([] if owned else ["--device", "/dev/video7"]),
                ),
                patch("tools.webcam.shutil.which", return_value="/usr/bin/tool"),
                patch("tools.webcam.allocate_camera", return_value=Path("/dev/video7")),
                patch("tools.webcam.Path.exists", return_value=True),
                patch("tools.webcam.os.access", return_value=True),
                patch("tools.webcam.validate_camera"),
                patch("tools.webcam.enable_preview"),
                patch("tools.webcam.subprocess.Popen") as popen,
                patch("tools.webcam.stop_process") as stop,
                patch("tools.webcam.subprocess.run") as run,
                patch("tools.webcam.os.geteuid", return_value=0),
            ):
                process = popen.return_value.__enter__.return_value
                process.wait.side_effect = KeyboardInterrupt
                self.assertEqual(webcam.main(), 0)
                stop.assert_called_once_with(process)
                if owned:
                    run.assert_called_once_with(
                        ["v4l2loopback-ctl", "delete", "/dev/video7"], check=True
                    )
                else:
                    run.assert_not_called()

    def test_producer_escalates_only_after_terminate_timeout(self) -> None:
        process = MagicMock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("ffmpeg", 3), 0]
        webcam.stop_process(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()

    def test_real_camera_is_rejected(self) -> None:
        with (
            patch("tools.webcam.Path.stat") as stat_result,
            patch("tools.webcam.subprocess.run") as run,
        ):
            stat_result.return_value.st_mode = 0o020660
            run.return_value.stdout = "Driver name : uvcvideo"
            with self.assertRaisesRegex(ValueError, "non-loopback"):
                webcam.validate_camera(Path("/dev/video1"))


if __name__ == "__main__":
    unittest.main()
