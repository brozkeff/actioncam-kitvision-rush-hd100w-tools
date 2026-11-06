package net.brozkeff.kitvisionrushtools

import android.net.Network
import java.io.Closeable
import java.net.InetSocketAddress
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.security.SecureRandom
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

class Camera(network: Network) : Closeable {
    private val socket = network.socketFactory.createSocket().apply { connect(InetSocketAddress("192.168.1.2", 6667), 15000); soTimeout = 15000 }
    private var sequence = SecureRandom().nextInt(256)
    private fun checksum(data: ByteArray): Int {
        var sum = 0L
        for (i in data.indices step 2) sum += (data[i].toInt() and 255) + (if (i + 1 < data.size) (data[i + 1].toInt() and 255) shl 8 else 0)
        while (sum shr 16 != 0L) sum = (sum and 65535) + (sum shr 16)
        return sum.toInt().inv() and 65535
    }
    private fun readExact(n: Int): ByteArray {
        val out = ByteArray(n); var offset = 0
        while (offset < n) { val count = socket.getInputStream().read(out, offset, n - offset); if (count < 0) error("Camera disconnected; operation outcome unknown"); offset += count }
        return out
    }
    fun request(family: Int, command: Int, payload: ByteArray = byteArrayOf(), timeout: Int = 200): ByteArray {
        sequence = (sequence + 1) and 255
        val b = ByteBuffer.allocate(14 + payload.size).order(ByteOrder.LITTLE_ENDIAN)
        b.put("DAEH".toByteArray()).putShort(b.capacity().toShort()).put(sequence.toByte()).put(family.toByte()).putShort(command.toShort()).putShort(timeout.toShort()).put(payload)
        b.putShort(checksum(b.array().copyOf(b.capacity() - 2)).toShort())
        socket.getOutputStream().write(b.array())
        val head = readExact(12); val h = ByteBuffer.wrap(head).order(ByteOrder.LITTLE_ENDIAN)
        require(String(head.copyOfRange(0, 4)) == "DAEH") { "Invalid reply header" }
        val length = h.getShort(4).toInt() and 65535
        require(length in 15..2048) { "Invalid reply length" }
        val all = head + readExact(length - 12); val reply = ByteBuffer.wrap(all).order(ByteOrder.LITTLE_ENDIAN)
        require((head[6].toInt() and 255) == sequence && (head[7].toInt() and 255) == family && (reply.getShort(8).toInt() and 65535) == (command or 0x8000)) { "Mismatched reply" }
        require(checksum(all.copyOf(all.size - 2)) == (reply.getShort(all.size - 2).toInt() and 65535)) { "Invalid checksum" }
        require(all[12].toInt() == 0) { "Camera rejected command: 0x%02x".format(all[12].toInt() and 255) }
        return all.copyOfRange(13, all.size - 2)
    }
    fun login() {
        val id = ByteArray(6); SecureRandom().nextBytes(id); id[0] = 2
        val challenge = request(0, 2, id); require(challenge.size == 12) { "Invalid challenge" }
        request(0, 3, "APPIOS".toByteArray().copyOf(16))
        request(0, 4, MessageDigest.getInstance("MD5").digest(challenge + "12345678".toByteArray()))
    }
    data class Status(val recording: Boolean, val battery: Int, val mode: String)
    fun status(): Status { val data = request(1, 3); require(data.size == 14 || data.size == 17); return Status(data[0].toInt() and 1 != 0, data[1].toInt() and 255, String(data.copyOfRange(2, 14)).trimEnd('\u0000')) }
    fun clock(): LocalDateTime { val s = String(request(1, 13), Charsets.US_ASCII); require(s.length == 12 && s.all { it in '0'..'9' }); val p = (0..10 step 2).map { s.substring(it, it + 2).toInt() }; return LocalDateTime.of(1970+p[0],p[1],p[2],p[3],p[4],p[5]) }
    fun setClock(value: LocalDateTime) { require(value.year in 1970..2069); val s = "%02d".format(Locale.ROOT, value.year - 1970) + value.format(DateTimeFormatter.ofPattern("MMddHHmmss", Locale.ROOT)); request(1, 25, s.toByteArray(Charsets.US_ASCII)) }
    fun modeRealtime() { request(255, 3, "Real_Time".toByteArray().copyOf(12), 10000) }
    fun record(start: Boolean) { request(1, if (start) 6 else 7, timeout = 10000) }
    override fun close() = socket.close()
}
