# Wi-Fi filesystem capture

## Hardware observations

Connected to camera `192.168.1.2` using Telnet and FTP. Shell reports BusyBox
1.15.0 and MIPS Linux 2.6.31--LSDK-9.2.0_U10.5.13, built August 2013.
Root filesystem is read-only squashfs; `/tmp` is RAM-backed.
Firmware labels: `W_D-3.0.00.030.bin`, `ap121-2.6.31/2013-08-14-11:34`.

Running services include `/bin/remote`, `/bin/http`, BusyBox httpd, lighttpd,
vsftpd, telnetd, DHCP and dnsmasq. Native remote binary references `/dev/remote`
and `/dev/CAM00`; these are investigation leads for camera communication.

## Captures

Ignored `tmp/camera/initial-telnet.bin` contains identity, processes, mounts,
flash partition layout and directory listings. `diagnostics-telnet.bin` contains
socket tables, memory, uptime, init configuration and kernel logs.
`files/` holds prioritized control binaries and web files. `rootfs/` holds the
persistent filesystem copy; `ftp-manifest.json` records transfer results.
The recursive FTP pass returned 255 file results totaling 7,637,620 bytes with
no queued directories remaining. This is a file-level copy, NOT a complete
flash image: symlinks and virtual filesystems were excluded. Direct FTP reads
of `/dev/mtdblock2` and `/dev/mtdblock3` failed. No firmware was written.
Raw captures may include credentials and remain excluded from Git.

## Clock distinction

Before any clock write, Wi-Fi Linux reported January 1, 1970, about 79 seconds
after boot. The supplied photo had a 2026 timestamp. This demonstrates that the
observed Linux clock was not tracking the photo timestamp at capture time.
The user subsequently set Linux time using `date -s`; BusyBox accepted hour 24
and normalized it to November 6, 2026 00:54 UTC. Persistence and influence on
recording timestamps remain unverified. The agent did not change camera time.

The user confirms `time.txt` was manually created following another guide and
did not work; it is not evidence of a camera-supported configuration format.
