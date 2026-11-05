"""Exercise snapshot validation without camera hardware."""

import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

from tools.rush import enable_preview, snapshot


class SnapshotTests(unittest.TestCase):
    def test_valid_invalid_and_existing_destination(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            body = b"\xff\xd8test\xff\xd9"
            mime = "image/jpeg"

            def do_GET(self) -> None:
                self.send_response(200)
                self.send_header("Content-Type", self.mime)
                self.end_headers()
                self.wfile.write(self.body)

            def log_message(self, *_args: object) -> None:
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        import urllib.request

        original = urllib.request.OpenerDirector.open

        def local_open(opener, request, **kwargs):
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/?action=snapshot"
            )
            return original(opener, request, **kwargs)

        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "snapshot.jpg"
                with patch.object(urllib.request.OpenerDirector, "open", local_open):
                    result = snapshot("192.168.1.2", 2, output)
                    self.assertEqual(result["bytes"], len(Handler.body))
                    self.assertEqual(output.read_bytes(), Handler.body)
                    with self.assertRaises(FileExistsError):
                        snapshot("192.168.1.2", 2, output)
                    Handler.body = b"not a jpeg"
                    with self.assertRaises(ValueError):
                        snapshot("192.168.1.2", 2, Path(directory) / "bad.jpg")
                    self.assertFalse((Path(directory) / "bad.jpg").exists())
                    Handler.body = b"\xff\xd8truncated"
                    with self.assertRaisesRegex(ValueError, "incomplete JPEG"):
                        snapshot("192.168.1.2", 2, Path(directory) / "truncated.jpg")
                    self.assertFalse((Path(directory) / "truncated.jpg").exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


class PreviewActivationTests(unittest.TestCase):
    def test_existing_listener_does_not_send_mode_switch(self) -> None:
        with (
            patch("tools.rush.port_open", return_value=True),
            patch("tools.rush.urllib.request.build_opener") as build,
        ):
            self.assertTrue(enable_preview("192.168.1.2", 1, 5)["preview_ready"])
            build.assert_not_called()

    def test_cgi_timeout_then_port_opens_sends_exactly_one_post(self) -> None:
        with (
            patch("tools.rush.port_open", side_effect=[False, False, True]),
            patch("tools.rush.time.sleep"),
            patch("tools.rush.urllib.request.build_opener") as build,
        ):
            build.return_value.open.side_effect = TimeoutError("CGI timeout")
            self.assertTrue(enable_preview("192.168.1.2", 1, 5)["preview_ready"])
            build.return_value.open.assert_called_once()
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.full_url, "http://192.168.1.2/cgi-bin/uvc")
            self.assertEqual(request.data, b"")

    def test_startup_timeout_is_failure(self) -> None:
        with (
            patch("tools.rush.port_open", return_value=False),
            patch("tools.rush.time.monotonic", side_effect=[0, 10]),
            patch("tools.rush.urllib.request.build_opener") as build,
        ):
            build.return_value.open.side_effect = TimeoutError("CGI timeout")
            with self.assertRaisesRegex(TimeoutError, "may have changed"):
                enable_preview("192.168.1.2", 1, 5)
            build.return_value.open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
