# Public fixed values from legacy software

These compatibility values are intentionally public. They were recovered from
the reference apps, firmware or owner-authorized connection tests. They are
not secrets belonging to a particular user. Do not substitute these constants
for the camera owner's actual configured Wi-Fi password.

| Value | Role | Evidence and limitation |
| --- | --- | --- |
| `192.168.1.2` | Camera IP | APK literal and hardware access |
| `6667/TCP` | Binary control | App and server initialization; tested |
| `80/TCP` | Web UI / CGI | Tested |
| `8080/TCP` | JPEG/MJPEG preview | Tested after UVC activation |
| `8083/TCP` | Filesystem HTTP | Static config and tested downloads |
| `8084/TCP` | Android real-time stream | APK literal; HTTP 200, body stalled |
| `root` / `root` | Telnet credentials | Login tested |
| `ap71` / empty password | FTP credentials | Login and downloads tested |
| `APPIOS` | Binary login username | Firmware compare and successful login |
| `12345678` | Binary login shared secret | Firmware/Android digest; tested |
| `DAEH` | Binary frame magic | App frame builder and received frames |
| `200` / `10000` | Header timeout fields | APK query / recording-mode paths |
| `123456789ABC` | USB serial string | Observed placeholder |
| `4255:1000` | External mass-storage USB ID | Linux USB descriptors |
| `4255:0001` | Internal camera custom USB ID | Driver alias and kernel log |
| `ACTIONPLUS` | 5aw-family default SSID | Firmware strings/default help text |

The binary username is padded to 16 bytes. Its shared secret is eight ASCII
bytes, with no trailing NUL included in the MD5 input. Authenticate by hashing
12 challenge bytes followed by those eight bytes; send the raw 16-byte digest.
See [the protocol specification](control.md) for the complete exchange.
This shared secret is not the Wi-Fi password and not the Telnet password.

## Other family defaults included in this firmware

The dump contains multiple product-family templates. Their presence does not
establish that a different camera model is supported by the Python tools.

| Template | Default SSID stated by firmware recovery text |
| --- | --- |
| 5aw | ACTIONPLUS |
| 5a1 | GAME |
| 3cg, 5bn, ebn | WIFIPODZ |
| def | DEFAULT |

All inspected wifiChange.txt templates literally print `Password:123456789.`.
The final full stop is present in the source text; whether it is punctuation
or part of the default password has NOT been checked by resetting credentials.
Do not claim a verified default WPA password from that text alone. The active
Wi-Fi password and client-specific configuration are excluded from public docs.
No recovery/reset trigger was activated to test these defaults.

## Current camera identity

Authenticated binary queries returned model `SV5AW`, camera firmware
`V1.3.10.020`, Wi-Fi firmware `3.0.00.030` and protocol version `0x13`.
Those identify two firmware components, not four interchangeable version tags.

These fixed credentials and exposed services are a security weakness for any
client able to join the hotspot. See [the threat notes](../security.md).
