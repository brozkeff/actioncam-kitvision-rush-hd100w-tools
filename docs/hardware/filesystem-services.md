# Camera filesystem and services

This inventory describes the inspected Rush HD100W, camera model `SV5AW`,
camera firmware `V1.3.10.020` and Wi-Fi firmware `W_D-3.0.00.030.bin`.
It is a simplified map, not a complete filesystem image or a claim about
other firmware. The persistent files were downloaded over FTP on 2026-11-05;
Telnet supplied shell, process and filesystem observations. On 2026-11-06,
read-only Telnet commands checked running processes and available versions.

The FTP copy contains 255 files. It did not capture every symlink, virtual
filesystem, device node or transient runtime file. `/var` and the SD mount
can change; their contents should not be treated as a firmware inventory.
The private copies remain in ignored `tmp/camera/rootfs/` and the manifest in
`tmp/camera/ftp-manifest.json`. They are not distributed with this project.

## Simplified tree

```text
/
├── 3cg/ 5a1/ 5aw/ 5bn/ def/ ebn/   model-specific web assets/configuration
├── bin/
│   ├── busybox                      shell and embedded utilities
│   ├── remote                       binary camera control bridge
│   ├── http                         camera HTTP service
│   ├── mjpg_streamer                MJPEG preview executable
│   ├── dnsmasq                      DNS/DHCP-capable daemon
│   ├── getsetting                   camera configuration/model selection
│   └── ...                          other programs and update helpers
├── cgi-bin/                         web UI handlers, including uvc and realtime
├── css/ images/ js/                 shared web UI assets
├── dev/                             runtime device nodes, including /dev/remote
├── etc/
│   ├── inittab                      starts /etc/rc.d/rcS
│   ├── rc.d/                        boot, network and USB mount scripts
│   ├── ath/                         wireless access-point scripts/configuration
│   ├── lighttpd.conf                HTTP server configuration
│   ├── udhcpd.conf                  DHCP server configuration
│   └── vsftpd.conf                  FTP server configuration
├── lib/
│   ├── modules/                     Wi-Fi and USB kernel modules
│   ├── rt_mode_class.ko             internal camera USB mode driver
│   ├── input_uvc.so output_http.so  preview plugins
│   └── libuClibc-0.9.30.so ...     runtime libraries
├── mnt/ proc/ sys/                  mount points and kernel interfaces
├── polaroid/                        alternate product web assets/scripts
├── sbin/                            hostapd, lighttpd, vsftpd, wireless tools
├── tmp/                             volatile runtime data
│   └── ftp/SDdisk/                  camera SD card mount when available
├── usr/                             additional utilities and web assets
├── var/                             runtime files, logs and leases
├── index.html uvc.html ...          top-level UI files
├── ver.log                          Wi-Fi firmware identifier
└── version                          platform build identifier
```

The root filesystem was observed as read-only squashfs; runtime mounts and
links are not faithfully represented by the FTP copy. The local tree can be
examined with `find tmp/camera/rootfs -print` when the private dump is present.
Avoid publishing its configuration, logs, vendor binaries or personal media.

## Services and versions

Port assignments are based on the earlier TCP scan and service configuration;
runtime process presence alone does not prove which executable owns a socket.
UDP was not scanned. Versions are exactly as reported by the indicated source;
unknown versions have not been guessed.

| Service | Executable / endpoint | Version and evidence |
| --- | --- | --- |
| Telnet | `/usr/sbin/telnetd`, TCP 23 | BusyBox 1.15.0; login banner |
| Web UI | `/usr/sbin/httpd -h /`, TCP 80 | BusyBox 1.15.0; boot script |
| DHCP | `/usr/sbin/udhcpd` | BusyBox 1.15.0; boot script |
| FTP | `/sbin/vsftpd`, TCP 21 | 2.3.4 embedded in the downloaded executable |
| DNS | `/bin/dnsmasq`, TCP 53 observed | 2.52; live `dnsmasq --version` |
| Static HTTP | `/sbin/lighttpd`, TCP 8083 | 1.4.20; live `lighttpd -v` |
| Wireless AP | `hostapd` | `v0.8.x`; live `hostapd -v` |
| Camera control | `/bin/remote`, TCP 6667 | Unknown; protocol `0x13` |
| Camera HTTP | `/bin/http`, TCP 8084 | Port bind is present in the active service binary and boot script |
| Preview | TCP 8080 when enabled | HTTP plugin says `MJPG-Streamer/0.2` |

The `MJPG-Streamer/0.2` string is an embedded server identifier, not a
verified precise source revision or proof of the process serving a given
request. DNS service behavior and UDP ports remain unverified. Process lists
and open ports can vary with camera mode; port 8080 is not always listening.
The `/bin/http` service is started by `/etc/rc.d/rcS`; its MIPS binary contains
the TCP 8084 bind and HTTP file-response code. See [port 8084 analysis](../findings/2026-11-06-port-8084.md).
The lighttpd build date is 2012-09-06. The 2026-11-06 process list also
contained `factoryreset` and serial `getty`.

System identifiers from live Telnet: Linux
`2.6.31--LSDK-9.2.0_U10.5.13`, build `#163` from 2013-08-06, MIPS;
`/version` contains `ap121-2.6.31/2013-08-14-11:34`. These are firmware build
identifiers, not version numbers for every bundled service.

See [network exposure](../security.md) for tested authentication and access;
the versions alone do not establish vulnerability or exploitability.
