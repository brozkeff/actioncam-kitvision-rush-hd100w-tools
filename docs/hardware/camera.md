# Camera identity and operating modes

Observed from USB: Ambarella Storage, VID:PID `4255:1000`, mass-storage/SCSI
bulk-only, endpoints OUT `0x01`, IN `0x81`. No USB network or video interface
was exposed. Without SD card the removable disk has zero capacity.
Do not infer GoPro protocol compatibility from the USB database display name.

Observed from local sample EXIF: Kondor Limited Rush HD100W,
software `V1.3.10.020`. Personal sample remains excluded from Git.

## Mode matrix

| Mode | Status | Pending validation |
| --- | --- | --- |
| USB without SD | Observed | Configuration unavailable as mounted files |
| USB with SD | Disconnects | Cause and configuration apply |
| Wi-Fi | Services and clock read/write | Recording and clock persistence |
| Wi-Fi with USB | Pending | Concurrent control and recording restrictions |

Insert SD only with power off. Use a card without irreplaceable data.

## Wi-Fi and stream identity

Wi-Fi Linux firmware reports `W_D-3.0.00.030.bin`, built in August 2013,
separately from EXIF software V1.3.10.020. The host used a separate Wi-Fi
interface while Ethernet retained internet access. Live MJPEG frames decoded at
320x240.
The page displays them at 512x384; display size is not source resolution.

SD-backed USB repeatedly disappears roughly six seconds after enumeration.
The same SD is readable through an external reader, so a bad filesystem has
not been established as the cause. No format or reset was attempted.

Authenticated binary identity now confirms internal model SV5AW and camera
firmware V1.3.10.020, consistent with the original photo's EXIF.
