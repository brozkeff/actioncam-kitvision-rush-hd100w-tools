# External SD card inspection

## Observations

The user reports repeatable USB removal roughly six seconds after SD-backed
storage enumeration. An external reader mounted the same FAT card successfully.
The camera was connected without its SD card during that inspection.
Inspection was read-only; no card files were modified.

Card root contains `DCIM/`, `System Volume Information/`, `actionplus.app/`,
`actionplus.exe`, `time.txt` (19 bytes), and `wifiChange.txt` (444 bytes).
A recursive filename search found neither `ActionConfig` nor `ActionCamera.bin`.
Their absence on this card does not establish whether camera USB exposes virtual
files or whether the app creates configuration files itself.

`time.txt` contains `2026-11-05 21:03:00` followed by a newline. Its presence is
not evidence that this firmware reads it or applies its timestamp.

`wifiChange.txt` documents a password recovery trigger: renaming it to
`PleaseChangeWIFI.txt` and restarting Wi-Fi restores factory Wi-Fi settings.
This trigger was NOT activated. Credentials are omitted from documentation.

## Next investigation

Trace the desktop app path construction and default configuration creation to
explain missing configuration files before attempting a write.
The user subsequently confirmed creating `time.txt` manually from another
guide; it did not set camera time. Do not treat it as firmware-generated.
