# Boot and service analysis

## Static evidence

- Init runs `/etc/rc.d/rcS`; persistent root is squashfs.
- Startup calls `remote convertprotocol` and `getsetting` before networking.
- `getsetting` selects web assets from several model-family directories:
  `5a1`, `5aw`, `5bn`, `3cg`, `ebn`. Their presence does not identify our family.
- Startup loads USB storage and `rt_mode_class.ko`, starts remote, HTTP, FTP,
  DHCP, DNS and Telnet services, then mounts camera storage under
  `/tmp/ftp/SDdisk` when available.
- usb_mount.sh retries mounting five times, with two-second sleeps; it supports
  vfat and an exFAT helper. A missing card therefore does not stop startup.
- Boot scripts contain SD-file-triggered recovery and firmware-update paths.
  Do not reproduce these trigger files during normal experiments.
- Different rcS variants exist; `/etc/inittab` selects the unsuffixed rcS.
- Legacy web assets mention MJPEG snapshot port 8080. It was closed in our scan;
  it later opened after preview activation. See the preview protocol notes.
- Lighttpd serves root `/` on port 8083. Avoid publishing captured configuration
  or raw filesystem contents; dumps remain gitignored.

## User-reported runtime observation

- top reports about 13.5 MiB visible memory: 8720 KiB used, 5064 KiB free.
- CPU roughly 97% idle at that instant; no obvious CPU saturation.
- factoryreset blocks in state D on `/dev/freset`; this alone does not prove a
  crash or explain automatic shutdown. It may be waiting for a device event.
- Repeated `/bin/http` entries are consistent with its worker architecture;
  they are not independently evidence of duplicate accidental launches.
- No daemon was killed or disabled during this investigation.
