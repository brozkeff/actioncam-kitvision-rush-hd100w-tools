"""Independently implemented Rush binary control framing and legacy login."""

import datetime as dt
import hashlib
import secrets
import socket
import struct
import time
from dataclasses import dataclass
from typing import Self

HEADER = struct.Struct("<4sHBBHH")
MAX_FRAME = 2048


class ProtocolError(ValueError):
    """Malformed frame or camera-reported failure."""


def checksum(data: bytes) -> int:
    """Calculate the protocol ones-complement checksum over little-endian words.

    An odd final byte is padded with zero in the high byte.

    Args:
        data: Frame bytes excluding the checksum trailer.

    Returns:
        Folded 16-bit checksum.
    """
    padded = data + b"\0" if len(data) % 2 else data
    total = sum(value[0] for value in struct.iter_unpack("<H", padded))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


@dataclass(frozen=True)
class Frame:
    """Represent a single request or reply in the camera binary protocol."""

    sequence: int
    family: int
    command: int
    payload: bytes
    timeout_field: int = 200

    def encode(self) -> bytes:
        """Serialize this frame, including its length and checksum.

        Returns:
            Wire-format frame bytes.

        Raises:
            ProtocolError: If the frame exceeds the supported size.
        """
        length = 14 + len(self.payload)
        if length > MAX_FRAME:
            raise ProtocolError("Frame exceeds camera buffer")
        header = HEADER.pack(
            b"DAEH",
            length,
            self.sequence,
            self.family,
            self.command,
            self.timeout_field,
        )
        body = header + self.payload
        return body + struct.pack("<H", checksum(body))

    @classmethod
    def decode(cls, data: bytes) -> Self:
        """Validate and parse a complete camera frame.

        Args:
            data: Complete frame including checksum.

        Returns:
            Decoded frame.

        Raises:
            ProtocolError: If length, magic or checksum is invalid.
        """
        if not 14 <= len(data) <= MAX_FRAME:
            raise ProtocolError("Invalid frame size")
        magic, length, sequence, family, command, field = HEADER.unpack(data[:12])
        if magic != b"DAEH" or length != len(data):
            raise ProtocolError("Bad magic or length")
        if checksum(data[:-2]) != struct.unpack("<H", data[-2:])[0]:
            raise ProtocolError("Invalid checksum")
        return cls(sequence, family, command, data[12:-2], field)


class Camera:
    """Manage one sequential TCP session with the camera control service."""

    def __init__(self, host: str, timeout: float = 5):
        """Initialize a disconnected session with a randomized sequence number.

        Args:
            host: Camera IPv4 address.
            timeout: Maximum time in seconds for each exchange.
        """
        self.host = host
        self.timeout = timeout
        self.connection: socket.socket | None = None
        self.sequence = secrets.randbelow(256)

    def __enter__(self) -> Self:
        """Connect the session.

        Returns:
            This camera session.
        """
        self.connection = socket.create_connection((self.host, 6667), self.timeout)
        return self

    def __exit__(self, *_args: object) -> None:
        """Close the session and discard any pending reply.

        Args:
            *_args: Context-manager exception details, if any.
        """
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def request(
        self,
        family: int,
        command: int,
        payload: bytes = b"",
        *,
        timeout_field: int = 200,
    ) -> bytes:
        """Exchange one command and invalidate the session after a transport or protocol error.

        Closing prevents a delayed reply from being mistaken for a later command.

        Args:
            family: Protocol command family.
            command: Command number.
            payload: Command-specific bytes.
            timeout_field: Timeout value sent to the camera, distinct from socket timeout.

        Returns:
            Reply data after the success status byte.
        """
        try:
            return self._exchange(family, command, payload, timeout_field=timeout_field)
        except OSError, ProtocolError:
            # A late reply must never be mistaken for the next operation.
            self.__exit__()
            raise

    def _exchange(
        self,
        family: int,
        command: int,
        payload: bytes = b"",
        *,
        timeout_field: int = 200,
    ) -> bytes:
        """Send one command and validate its reply under a single deadline.

        Writes are never retried because a timed-out operation may have succeeded.

        Args:
            family: Protocol command family.
            command: Command number.
            payload: Command-specific bytes.
            timeout_field: Timeout value encoded in the request.

        Returns:
            Reply data after the success status byte.
        """
        if self.connection is None:
            raise RuntimeError("Camera connection is not open")
        connection = self.connection
        self.sequence = (self.sequence + 1) & 255
        request = Frame(self.sequence, family, command, payload, timeout_field)
        deadline = time.monotonic() + self.timeout
        connection.settimeout(self.timeout)
        connection.sendall(request.encode())

        def receive(size: int) -> bytes:
            """Read exactly the requested bytes within the exchange deadline.

            Args:
                size: Number of bytes expected.

            Returns:
                Complete requested data.
            """
            parts = bytearray()
            while len(parts) < size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        "Camera response deadline expired; operation outcome unknown"
                    )
                connection.settimeout(remaining)
                part = connection.recv(size - len(parts))
                if not part:
                    raise ConnectionError(
                        "Camera disconnected during reply; operation outcome unknown"
                    )
                parts.extend(part)
            return bytes(parts)

        prefix = receive(12)
        magic, length, *_ = HEADER.unpack(prefix)
        if magic != b"DAEH" or not 15 <= length <= MAX_FRAME:
            raise ProtocolError("Invalid reply header")
        response = Frame.decode(prefix + receive(length - 12))
        if (response.sequence, response.family, response.command) != (
            self.sequence,
            family,
            command | 0x8000,
        ):
            raise ProtocolError("Reply does not match request")
        if not response.payload:
            raise ProtocolError("Reply lacks status")
        if response.payload[0]:
            raise ProtocolError(
                f"Camera rejected family={family} command=0x{command:04x}: status=0x{response.payload[0]:02x}"
            )
        return response.payload[1:]

    def authenticate(self) -> None:
        # Shared compatibility values recovered from the shipped app/firmware;
        # intentionally public. This is not a user-specific password.
        """Log in using the vendor protocol shared compatibility values."""
        client_id = b"\x02" + secrets.token_bytes(5)
        challenge = self.request(0, 2, client_id)
        if len(challenge) != 12:
            raise ProtocolError("Expected 12-byte challenge")
        self.request(0, 3, b"APPIOS".ljust(16, b"\0"))
        digest = hashlib.md5(challenge + b"12345678", usedforsecurity=False).digest()
        self.request(0, 4, digest)

    def version(self) -> dict[str, str | int]:
        """Query protocol and Wi-Fi firmware versions.

        Returns:
            Version fields reported by the camera.
        """
        version = self.request(0, 1, b"\0")
        wifi = self.request(2, 1, b"3.0.00.030".ljust(17, b"\0"))
        if len(version) != 1:
            raise ProtocolError("Unexpected protocol version reply")
        return {
            "protocol": version[0],
            "wifi_firmware": wifi.rstrip(b"\0").decode("ascii"),
        }

    def status(self) -> dict[str, str | int]:
        """Read status flags, battery and mode while retaining raw data.

        Returns:
            Decoded status fields and original bytes as hexadecimal.
        """
        data = self.request(1, 3)
        if len(data) not in (14, 17):
            raise ProtocolError(f"Unexpected status length: {len(data)}")
        return {
            "battery_percent": data[1],
            "flags_raw": data[0],
            "recording": bool(data[0] & 1),
            "mode": data[2:14].rstrip(b"\0").decode("ascii"),
            "raw": data.hex(),
        }

    def identity(self) -> dict[str, str]:
        """Read the recording processor model and firmware.

        Returns:
            Camera model and firmware identifiers.
        """
        firmware = self.request(1, 1, b"\0" * 17)
        model = self.request(1, 2, b"\0" * 16)
        return {
            "camera_firmware": firmware.rstrip(b"\0").decode("ascii"),
            "camera_model": model.rstrip(b"\0").decode("ascii"),
        }

    def settings(self) -> dict[str, str]:
        """Read the supported settings without modifying them.

        Returns:
            Setting names mapped to decoded camera values.
        """
        names = {
            8: "photo_resolution",
            9: "photo_mode",
            10: "fhd_resolution",
            11: "hd_resolution",
            12: "tv_system",
            14: "auto_power_raw",
            15: "auto_rotation",
            16: "language",
            17: "mode",
        }
        values = {
            name: self.request(1, command).split(b"\0", 1)[0].decode("ascii")
            for command, name in names.items()
        }
        values["camera_clock"] = self.clock().isoformat()
        return values

    def clock(self) -> dt.datetime:
        """Read the recording clock, whose year is encoded relative to 1970.

        Returns:
            Naive camera wall time; the protocol carries no timezone.
        """
        value = self.request(1, 13)
        if len(value) != 12 or not value.isdigit():
            raise ProtocolError("Invalid clock reply")
        parts = [int(value[i : i + 2]) for i in range(0, 12, 2)]
        return dt.datetime(
            1970 + parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        )

    def set_clock(self, value: dt.datetime) -> None:
        """Set the recording processor clock with the dedicated command.

        Args:
            value: Wall time to encode; timezone information is not transmitted.

        Raises:
            ValueError: If the year cannot be represented by the camera.
        """
        if not 1970 <= value.year <= 2069:
            raise ValueError("Camera clock year must be 1970–2069")
        payload = (f"{value.year - 1970:02d}" + value.strftime("%m%d%H%M%S")).encode(
            "ascii"
        )
        self.request(1, 25, payload)

    def mode(self, mode: str) -> None:
        """Request a camera mode change; behavior depends on camera state.

        Args:
            mode: Either Real_Time or Mass_Storage.

        Raises:
            ValueError: If the mode is unsupported.
        """
        if mode not in ("Real_Time", "Mass_Storage"):
            raise ValueError("Unsupported mode")
        self.request(255, 3, mode.encode().ljust(12, b"\0"), timeout_field=10000)

    def record(self, start: bool) -> None:
        """Send the experimental recording start or stop command once.

        Args:
            start: True to start, false to stop.
        """
        self.request(1, 6 if start else 7, timeout_field=10000)
