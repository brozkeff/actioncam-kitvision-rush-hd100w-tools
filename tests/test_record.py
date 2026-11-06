"""Managed recording identification and uncertain stop behavior."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import record


class RecordingTests(unittest.TestCase):
    def test_capture_downloads_only_new_video(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "video.mov"
            with (
                mock.patch.object(
                    record,
                    "camera_status",
                    return_value={"mode": "Mass_Storage", "recording": False},
                ),
                mock.patch.object(
                    record,
                    "videos",
                    side_effect=[
                        {"100MEDIA/old.MOV"},
                        {"100MEDIA/old.MOV", "100MEDIA/new.MOV"},
                    ],
                ),
                mock.patch.object(record, "change_mode") as mode,
                mock.patch.object(record, "record_command") as command,
                mock.patch.object(record, "download") as download,
            ):
                self.assertEqual(
                    record.capture("camera", target, lambda: None, lambda _: None),
                    "100MEDIA/new.MOV",
                )
            self.assertEqual(
                mode.call_args_list,
                [mock.call("camera", "Real_Time"), mock.call("camera", "Mass_Storage")],
            )
            self.assertEqual(
                command.call_args_list,
                [mock.call("camera", True), mock.call("camera", False)],
            )
            download.assert_called_once_with("camera", "100MEDIA/new.MOV", target)

    def test_ambiguous_video_is_never_downloaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(
                    record,
                    "camera_status",
                    return_value={"mode": "Mass_Storage", "recording": False},
                ),
                mock.patch.object(
                    record, "videos", side_effect=[set(), {"a.MOV", "b.MOV"}]
                ),
                mock.patch.object(record, "change_mode"),
                mock.patch.object(record, "record_command"),
                mock.patch.object(record, "download") as download,
                self.assertRaisesRegex(RuntimeError, "2 new videos"),
            ):
                record.capture(
                    "camera",
                    Path(directory) / "out.mov",
                    lambda: None,
                    lambda _: None,
                )
            download.assert_not_called()

    def test_unverified_stop_never_switches_to_storage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(
                    record,
                    "camera_status",
                    side_effect=[
                        {"mode": "Mass_Storage", "recording": False},
                        {"recording": True},
                    ],
                ),
                mock.patch.object(record, "videos", return_value=set()),
                mock.patch.object(record, "change_mode") as mode,
                mock.patch.object(
                    record,
                    "record_command",
                    side_effect=[None, RuntimeError("bad reply")],
                ),
                self.assertRaisesRegex(RuntimeError, "Stop could not be verified"),
            ):
                record.capture(
                    "camera",
                    Path(directory) / "out.mov",
                    lambda: None,
                    lambda _: None,
                )
            mode.assert_called_once_with("camera", "Real_Time")

    def test_existing_destination_does_not_touch_camera(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.mov"
            target.write_bytes(b"original")
            with (
                mock.patch.object(record, "camera_status") as status,
                self.assertRaises(FileExistsError),
            ):
                record.capture("camera", target, lambda: None)
            status.assert_not_called()
            self.assertEqual(target.read_bytes(), b"original")
