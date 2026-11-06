# Android build setup

This is an experimental Android 12+ camera controller. Connect to the camera's
Wi-Fi, then refresh status and camera time. Preview uses the camera's port 8080
JPEG endpoint and changes camera mode. Stop preview before other controls.
Recording controls are experimental. The camera photo command and media
downloads are not yet implemented. On the owner's Moto G85 running Android 16,
installation, launch, in-app Wi-Fi connection, status, system-bar layout and
preview have worked. Preview initially failed on both Android and Linux;
disconnecting and reconnecting camera power restored it. Recording and Android
clock writes still require hardware verification.
Version 0.1.2 detects existing Wi-Fi connections with a reachable camera control
port, avoiding a forced disconnect before connecting in the app. Credentials
are saved when connecting or pressing Save, encrypted with an Android Keystore
key in app-private storage excluded from backup. Forget removes the saved file.
The app does not log the credentials. Existing Wi-Fi detection does not keep a
system-managed Wi-Fi connection alive; reconnect through the app if Android
drops that network.

Check camera ports probes TCP ports 21, 23, 53, 80, 6667, 8080, 8083 and 8084
through the selected Wi-Fi network, without sending application commands.
OPEN means a TCP connection succeeded, not that the service is functioning.
Timeouts and other errors do not establish whether Android, the network or the
camera is responsible. Port 8080 is expected to be closed outside preview mode.

Open camera web interface launches the phone's default HTTP browser. For
external browser access, Android may require the camera Wi-Fi to be connected
in system settings, since an app-requested local-only network can be restricted
to the requesting app.

Install JDK 17, Android SDK platform 37 and build tools 37. On the Linux machine
used for this project, select the JDK and SDK for a shell session with:

```sh
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_HOME="$HOME/Android/Sdk"
cd android
./gradlew --version
./gradlew :app:exportDebugApk
adb install -r app/build/outputs/distributions/net.brozkeff.kitvisionrushtools-0.1.2-debug.apk
```

On macOS, set `JAVA_HOME` using `/usr/libexec/java_home -v 17` and set
`ANDROID_HOME` to the installed SDK path. The wrapper downloads its pinned
Gradle distribution and verifies its SHA-256 checksum. The JDK path is not
hard-coded in the project.


## Installing the downloadable APK

1. Download `net.brozkeff.kitvisionrushtools-0.1.2-debug.apk` from the project's
   GitHub release, along with `SHA256SUMS` if verifying the download.
2. Open the APK on an Android 12+ phone. If prompted, allow your browser or file
   manager to install unknown apps for this installation.
3. Google Play Protect may offer to scan this sideloaded app, including each new
   version. Allow the scan and review its result; keep Play Protect enabled.
   A scan request alone is not a malware finding. If it reports harmful behavior,
   stop and report the exact warning instead of bypassing it. See
   [Google's Play Protect explanation](https://support.google.com/googleplay/answer/2812853).
4. Launch Kitvision Rush Tools, enter camera Wi-Fi credentials and connect.
   Approve the system Wi-Fi and nearby-device permission requests. On Android 17,
   approve local-network permission too. Refresh status, then start preview.

The connection requested inside the app can be restricted to this app. Other
apps may keep using LTE/5G and a Wi-Fi status icon may not appear. For Firefox
access to the camera web UI, connect to camera Wi-Fi in Android system settings.
If preview port 8080 remains closed, a camera power reconnection recovered the
observed stuck state; first ensure recording has stopped.

## Build and signing details

The app ID is `net.brozkeff.kitvisionrushtools`; Android version `0.1.2` has version
code 3 and is included in project release `v0.0.12`. It uses Kotlin without native
libraries, so the same APK supports ARM64 phones and can be built on Linux x64
or macOS Apple Silicon. The pinned build uses Gradle 9.3.1 and AGP 9.1.1.

This first download is a **debug-signed experimental build**, not a Play Store
release. Android updates require the same application ID and signing key. The
build machine's private debug keystore must be preserved outside Git and release
assets. A different machine normally generates a different debug key; installing
that APK over this one will fail signature validation. Uninstalling allows a new
key but deletes local app data and saved credentials. Preserve the original key
for updates instead. Never publish a keystore, key password or private key.

In the agent's restricted build environment, the existing signing key is under
`tmp/android-home/debug.keystore`. Use this existing directory to retain update
compatibility:

```sh
# Run from the repository root after selecting JAVA_HOME and ANDROID_HOME.
export ANDROID_USER_HOME="$PWD/tmp/android-home"
export GRADLE_USER_HOME="$PWD/tmp/gradle-home"
./android/gradlew -p android -Pkotlin.compiler.execution.strategy=in-process :app:exportDebugApk
```

These paths are ignored local state. Back up the signing key privately before
cleaning `tmp/`. The release includes an APK SHA-256 checksum and signing
certificate fingerprint so downloads and signing identity can be checked.
