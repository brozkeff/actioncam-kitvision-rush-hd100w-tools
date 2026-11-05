"""Wire fixtures, fragmented replies, login and clock encoding."""

import datetime as dt
import hashlib
import unittest
from unittest.mock import MagicMock, patch

from tools.protocol import Camera, Frame, ProtocolError, checksum


class FrameTests(unittest.TestCase):
    def test_hardware_version_fixture(self) -> None:
        request = bytes.fromhex("444145480f0001000100c800009d75")
        reply = bytes.fromhex("444145481000010001800000001363e3")
        self.assertEqual(Frame(1, 0, 1, b"\0").encode(), request)
        self.assertEqual(Frame.decode(reply).payload, b"\0\x13")

    def test_odd_payload_and_corruption(self) -> None:
        for size in range(20):
            frame = Frame(255, 1, 13, bytes(range(size)))
            self.assertEqual(Frame.decode(frame.encode()), frame)
        corrupted = bytearray(Frame(1, 1, 3, b"abc").encode())
        corrupted[12] ^= 1
        with self.assertRaisesRegex(ProtocolError, "checksum"):
            Frame.decode(corrupted)
        with self.assertRaises(ProtocolError):
            Frame.decode(b"short")
        with self.assertRaises(ProtocolError):
            Frame(0, 0, 0, b"x" * 2048).encode()
        self.assertEqual(checksum(b"a"), 0xFF9E)


class CameraTests(unittest.TestCase):
    def test_fragmented_reply(self) -> None:
        reply = Frame(1, 1, 0x800D, b"\0" + b"561105224209", 0).encode()
        sock = MagicMock()
        sock.recv.side_effect = [reply[:5], reply[5:12], reply[12:15], reply[15:]]
        with (
            patch("tools.protocol.socket.create_connection", return_value=sock),
            Camera("192.168.1.2") as camera,
        ):
            camera.sequence = 0
            self.assertEqual(camera.clock(), dt.datetime(2026, 11, 5, 22, 42, 9))
        sock.close.assert_called_once()

    def test_timeout_invalidates_connection_and_never_retries_write(self) -> None:
        sock = MagicMock()
        sock.recv.side_effect = TimeoutError("timeout")
        with (
            patch("tools.protocol.socket.create_connection", return_value=sock),
            Camera("192.168.1.2") as camera,
        ):
            with self.assertRaises(TimeoutError):
                camera.record(True)
            self.assertIsNone(camera.connection)
            sock.sendall.assert_called_once()
            with self.assertRaises(RuntimeError):
                camera.record(True)

    def test_mismatched_sequence_rejected(self) -> None:
        reply = Frame(99, 1, 0x8003, b"\0", 0).encode()
        sock = MagicMock()
        sock.recv.side_effect = [reply[:12], reply[12:]]
        with (
            patch("tools.protocol.socket.create_connection", return_value=sock),
            Camera("192.168.1.2") as camera,
        ):
            camera.sequence = 0
            with self.assertRaisesRegex(ProtocolError, "match"):
                camera.request(1, 3)
            self.assertIsNone(camera.connection)

    def test_login_uses_documented_shared_values(self) -> None:
        challenge = b"012345678901"
        with patch.object(
            Camera, "request", side_effect=[challenge, b"", b""]
        ) as request:
            Camera("192.168.1.2").authenticate()
            self.assertEqual(
                request.call_args_list[1].args, (0, 3, b"APPIOS".ljust(16, b"\0"))
            )
            self.assertEqual(
                request.call_args_list[2].args,
                (0, 4, hashlib.md5(challenge + b"12345678").digest()),
            )

    def test_clock_write_is_separate_from_other_settings(self) -> None:
        with patch.object(Camera, "request", return_value=b"") as request:
            camera = Camera("192.168.1.2")
            camera.set_clock(dt.datetime(2026, 11, 5, 22, 42, 8))
            request.assert_called_once_with(1, 25, b"561105224208")
            with self.assertRaises(ValueError):
                camera.set_clock(dt.datetime(2070, 1, 1))
            request.assert_called_once()
