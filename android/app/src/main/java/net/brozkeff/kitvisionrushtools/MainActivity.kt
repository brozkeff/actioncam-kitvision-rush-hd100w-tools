package net.brozkeff.kitvisionrushtools

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.pm.PackageManager
import android.content.Intent
import android.content.ActivityNotFoundException
import android.net.Uri
import android.graphics.BitmapFactory
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiNetworkSpecifier
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.WindowInsetsController
import java.net.InetSocketAddress
import android.widget.*
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.time.Duration
import java.time.LocalDateTime
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    @Volatile private var network: Network? = null
    private var observer: ConnectivityManager.NetworkCallback? = null
    private val credentials by lazy { Credentials(this) }
    private var callback: ConnectivityManager.NetworkCallback? = null
    @Volatile private var preview = false
    private lateinit var status: TextView
    private lateinit var image: ImageView
    private lateinit var ssid: EditText
    private lateinit var password: EditText
    private val manager by lazy { getSystemService(ConnectivityManager::class.java) }
    private fun message(s: String) = runOnUiThread { status.text = s }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val scroll = ScrollView(this); val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(24,24,24,24) }; scroll.addView(box); setContentView(scroll)
        window.setDecorFitsSystemWindows(false)
        window.insetsController?.setSystemBarsAppearance(WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS, WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS)
        scroll.setOnApplyWindowInsetsListener { view, insets ->
            val safe = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout() or WindowInsets.Type.ime())
            view.setPadding(safe.left, safe.top, safe.right, safe.bottom)
            insets
        }
        scroll.requestApplyInsets()
        status = TextView(this).apply { text = "Disconnected"; textSize = 17f }; box.addView(status)
        ssid = EditText(this).apply { hint = "Camera Wi-Fi name" }; box.addView(ssid)
        password = EditText(this).apply { hint = "Wi-Fi password"; inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD }; box.addView(password)
        fun button(label: String, action: () -> Unit) { box.addView(Button(this).apply { text = label; setOnClickListener { action() } }) }
        try { credentials.load()?.let { (name, pass) -> ssid.setText(name); password.setText(pass) } }
        catch (_: Exception) { message("Saved Wi-Fi credentials could not be read. Please enter them again.") }
        password.importantForAutofill = android.view.View.IMPORTANT_FOR_AUTOFILL_NO
        password.isSaveEnabled = false
        button("Save Wi-Fi credentials") { try { credentials.save(ssid.text.toString(), password.text.toString()); message("Wi-Fi credentials saved on this device.") } catch (_: Exception) { message("Could not save Wi-Fi credentials.") } }
        button("Forget saved credentials") { credentials.clear(); ssid.setText(""); password.setText(""); message("Saved credentials removed.") }
        button("Connect to camera Wi-Fi") { connect() }
        button("Refresh status and camera time") { operation { c -> val s = c.status(); "Mode: ${s.mode}; battery: ${s.battery}%; recording: ${s.recording}\nCamera time: ${c.clock()}" } }
        button("Set camera time to phone time") { operation { c -> val value = LocalDateTime.now().withNano(0); c.setClock(value); val read = c.clock(); require(kotlin.math.abs(Duration.between(value, read).seconds) <= 5) { "Clock readback differs: $read" }; "Camera time set and verified: $read" } }
        button("Open camera web interface") {
            try { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("http://192.168.1.2/"))) }
            catch (_: ActivityNotFoundException) { message("No web browser is available.") }
        }
        button("Check camera ports") { scanPorts() }
        button("Start preview") { startPreview() }
        button("Stop preview") { preview = false; message("Preview stopped") }
        button("Start recording (experimental)") { confirmRecord(true) }
        button("Stop recording (experimental)") { confirmRecord(false) }
        box.addView(TextView(this).apply { text = "Camera photo capture is not yet verified and is unavailable." })
        image = ImageView(this).apply { adjustViewBounds = true }; box.addView(image, ViewGroup.LayoutParams(-1, 500))
        observeWifi()
    }
    private fun observeWifi() {
        val cb = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(net: Network) { worker.execute { adoptWifi(net) } }
            override fun onLost(net: Network) { if (network == net) { network = null; preview = false; message("Camera Wi-Fi disconnected.") } }
        }
        observer = cb
        manager.registerNetworkCallback(NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_WIFI).removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET).build(), cb)
    }
    private fun adoptWifi(net: Network): Boolean {
        if (network != null) return network == net
        return try {
            net.socketFactory.createSocket().use { it.connect(InetSocketAddress("192.168.1.2", 6667), 1500) }
            if (manager.getNetworkCapabilities(net)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) != true) return false
            network = net; message("Using existing Wi-Fi connection to camera. Refresh status to verify."); true
        } catch (_: Exception) { false }
    }
    private fun connect() {
        val perms = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= 33) perms.add(Manifest.permission.NEARBY_WIFI_DEVICES) else perms.add(Manifest.permission.ACCESS_FINE_LOCATION)
        if (Build.VERSION.SDK_INT >= 37) perms.add("android.permission.ACCESS_LOCAL_NETWORK")
        val missing = perms.filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) { requestPermissions(missing.toTypedArray(), 1); message("Grant permissions, then tap Connect again."); return }
        val name = ssid.text.toString(); val pass = password.text.toString()
        if (name.isBlank()) { message("Enter the camera Wi-Fi name."); return }
        try {
            credentials.save(name, pass)
            if (network != null) { message("Camera Wi-Fi already connected."); return }
            worker.execute {
                val existing = manager.allNetworks.firstOrNull { manager.getNetworkCapabilities(it)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true && adoptWifi(it) }
                if (existing == null) runOnUiThread { requestWifi(name, pass) }
            }
        } catch (_: Exception) { message("Could not save credentials or use Wi-Fi. Check permissions.") }
    }
    private fun requestWifi(name: String, pass: String) {
        try {
            callback?.let { manager.unregisterNetworkCallback(it) }; network = null; preview = false
            val builder = WifiNetworkSpecifier.Builder().setSsid(name); if (pass.isNotEmpty()) builder.setWpa2Passphrase(pass)
            val request = NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_WIFI).removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET).setNetworkSpecifier(builder.build()).build()
            val cb = object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(net: Network) { network = net; message("Camera Wi-Fi connected. Refresh status to verify camera.") }
                override fun onUnavailable() { network = null; message("Camera Wi-Fi unavailable or request declined.") }
                override fun onLost(net: Network) { if (network == net) { network = null; preview = false; message("Camera Wi-Fi disconnected.") } }
            }
            callback = cb; manager.requestNetwork(request, cb); message("Approve the Android Wi-Fi connection request.")
        } catch (e: Exception) { message("Connection failed: ${e.message}") }
    }
    private fun scanPorts() {
        val net = network ?: return message("Connect camera Wi-Fi first.")
        if (preview) return message("Stop preview before checking ports.")
        message("Checking camera TCP ports…")
        worker.execute {
            val results = mutableListOf("Camera TCP ports (192.168.1.2):")
            for ((port, label) in listOf(21 to "FTP", 23 to "Telnet", 53 to "DNS candidate", 80 to "Web / preview activation", 6667 to "Camera control", 8080 to "Preview (mode dependent)", 8083 to "Filesystem HTTP", 8084 to "Camera stream HTTP")) {
                if (network != net) { results.add("Network changed; scan stopped."); break }
                val outcome = try { net.socketFactory.createSocket().use { it.connect(InetSocketAddress("192.168.1.2", port), 1500) }; "OPEN" }
                    catch (e: java.net.SocketTimeoutException) { "TIMEOUT" }
                    catch (e: Exception) { "UNREACHABLE: ${e.javaClass.simpleName}: ${e.message}" }
                results.add("$port $label: $outcome")
                message(results.joinToString("\n"))
            }
        }
    }
    private fun operation(block: (Camera) -> String) {
        val net = network ?: return message("Connect camera Wi-Fi first.")
        if (preview) return message("Stop preview before camera control operations.")
        message("Contacting camera…")
        worker.execute { try { Camera(net).use { c -> c.login(); message(block(c)) } } catch (e: Exception) { message("Camera operation failed: ${e.message}. If a write was sent, refresh status before retrying.") } }
    }
    private fun confirmRecord(start: Boolean) {
        AlertDialog.Builder(this).setMessage("Recording control is experimental. The camera may reject commands or become unresponsive. Continue?").setNegativeButton("Cancel", null).setPositiveButton("Continue") { _, _ ->
            preview = false
            operation { c -> val before = c.status(); if (before.recording != start) { if (start && before.mode != "Real_Time") { message("Switching camera to realtime mode…"); c.modeRealtime(); Thread.sleep(2000); val mode = c.status(); require(mode.mode == "Real_Time") { "Realtime mode not confirmed" } }; message(if (start) "Sending recording start…" else "Sending recording stop…"); c.record(start) }; var after = c.status(); val deadline = android.os.SystemClock.elapsedRealtime() + 2000; while (after.recording != start && android.os.SystemClock.elapsedRealtime() < deadline) { Thread.sleep(250); after = c.status() }; require(after.recording == start) { "Recording state not confirmed" }; "Recording: ${after.recording}; mode: ${after.mode}" }
        }.show()
    }
    private fun startPreview() {
        val net = network ?: return message("Connect camera Wi-Fi first.")
        if (preview) return
        preview = true
        worker.execute {
            try {
                Camera(net).use { c -> c.login(); require(!c.status().recording) { "Stop recording before activating preview" } }
                message("Checking preview service…")
                fun listening(): Boolean = try { net.socketFactory.createSocket().use { it.connect(InetSocketAddress("192.168.1.2", 8080), 500) }; true } catch (_: java.io.IOException) { false }
                if (!listening()) {
                message("Activating preview; waiting for camera…")
                val connection = net.openConnection(URL("http://192.168.1.2/cgi-bin/uvc")) as HttpURLConnection
                connection.requestMethod = "POST"; connection.doOutput = true; connection.setFixedLengthStreamingMode(0); connection.connectTimeout = 3000; connection.readTimeout = 12000; connection.setRequestProperty("Referer", "http://192.168.1.2/uvc.html")
                var activation = "HTTP request sent"
                try { connection.outputStream.use { }; activation = "HTTP ${connection.responseCode}"; connection.inputStream.close() } catch (_: java.net.SocketTimeoutException) { activation = "CGI timed out; activation may still be running" } finally { connection.disconnect() }
                val deadline = android.os.SystemClock.elapsedRealtime() + 60000
                while (preview && network == net && !listening()) {
                    check(android.os.SystemClock.elapsedRealtime() < deadline) { "Preview port 8080 stayed closed after 60 seconds ($activation). Camera preview startup failed or port is unreachable; refresh status to check mode" }
                    Thread.sleep(250)
                }
                }
                message("Reading preview frames…")
                var failures = 0
                while (preview && network == net) {
                    try { val c = net.openConnection(URL("http://192.168.1.2:8080/?action=snapshot&n=${System.nanoTime()}")) as HttpURLConnection; c.connectTimeout = 3000; c.readTimeout = 3000
                        val bytes = try { c.inputStream.use { input -> val out = ByteArrayOutputStream(); val buffer = ByteArray(8192); while (out.size() <= 2_000_000) { val n = input.read(buffer); if (n < 0) break; out.write(buffer, 0, n) }; out.toByteArray() } } finally { c.disconnect() }; require(bytes.size <= 2_000_000); val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: error("Invalid JPEG"); failures = 0; runOnUiThread { if (preview) { image.setImageBitmap(bitmap); status.text = "Preview active" } }
                    } catch (e: Exception) { message("Preview frame failed ($failures): ${e.message}"); if (++failures > 3) throw e }; Thread.sleep(250)
                }
            } catch (e: Exception) { message("Preview failed: ${e.message}") } finally { preview = false }
        }
    }
    override fun onDestroy() { preview = false; callback?.let { manager.unregisterNetworkCallback(it) }; observer?.let { manager.unregisterNetworkCallback(it) }; worker.shutdownNow(); super.onDestroy() }
}
