# Android companion app network behavior

## Static analysis

The reference APK `apps/android-apk/actionplusremote.apk` was decoded offline
with apktool. The APK is package `com.action.remote`, version `V1.6.0`, with
minimum SDK 10 and target SDK 15. No vendor code was executed.

The app dynamically registers `WifiReceiver` for connectivity changes from its
main activities. Each receiver invocation starts `NatService` on a background
thread. That service has a once-per-day gate in shared preferences, performs
STUN-based NAT detection, and then posts an XML record to
`http://cloud.developer.skli.biz:8888/sklcloud/skl-cloud/test/app/nat/uploadInfo`
over plain HTTP. The record builder supplies the network type, ISP/carrier,
detected NAT/router type and the fixed app name `Action+ Remote`; several other
XML fields remain empty by default. For Wi-Fi connections, the code obtains the
public IP through STUN and requests ISP information from
`http://ip.taobao.com/service/getIpInfo.php`. The APK also contains a STUN
endpoint at `p2p-stun.developer.skli.biz:3478`.

This is code-path evidence of periodic network metadata transmission, not a
captured request. The code shown does not add the Wi-Fi passphrase or local
device MAC to the XML upload. The cloud endpoint's current ownership, operation
and data retention are unknown. A legacy third-party IP lookup is also present;
its live behavior was not tested.

## Camera control leads

The APK's native JNI library exports protocol functions for CHAP, version and
status queries, preview mode, recording start/stop, photo capture, settings,
SSID/password changes, firmware update, card format and camera restart. The
Java preview path contains `http://192.168.1.2:8084/?stream`; this differs from
the currently verified preview endpoints and remains an app-originated lead,
not evidence that the endpoint works on this camera. The APK also contains
strings `root` / `root` for an FTP host at `192.168.1.2`; these defaults were
not exercised.

## Windows companion app: preliminary static inventory

`apps/windows/actionplus.exe` is a 32-bit PE GUI executable with a PE timestamp
of 2013-08-13 and embedded product version `1.0.10.009`. Its imports include
common MFC/UI libraries and file APIs (`CreateFile`, `ReadFile`, `WriteFile`,
file-size and file-time functions). The import table does not list Winsock,
WinHTTP or WinINet. Static UI strings identify date/time, photo mode,
resolution and time-lapse controls, and report a camera-connection error. This
is consistent with a desktop utility that reads or writes camera data through
files or another non-network interface, but does not prove the transport or
the implementation of those operations. No Windows code was executed and no
protocol conclusion is made yet.
