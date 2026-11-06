package net.brozkeff.kitvisionrushtools

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import org.json.JSONObject
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Device-local credentials; ciphertext is excluded from backup and keys never leave Keystore. */
class Credentials(context: Context) {
    private val file = AtomicFile(File(context.noBackupFilesDir, "camera-wifi"))
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("camera-wifi", null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("camera-wifi", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    fun save(ssid: String, password: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
        val encrypted = cipher.doFinal(JSONObject().put("ssid", ssid).put("password", password).toString().toByteArray(Charsets.UTF_8))
        val stream = file.startWrite()
        try { stream.write(cipher.iv.size); stream.write(cipher.iv); stream.write(encrypted); file.finishWrite(stream) }
        catch (e: Exception) { file.failWrite(stream); throw e }
    }
    fun load(): Pair<String, String>? {
        if (!file.baseFile.exists()) return null
        val data = file.readFully(); val length = data[0].toInt() and 255
        require(length == 12 && data.size > length + 16)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, data.copyOfRange(1, 1 + length))) }
        val json = JSONObject(String(cipher.doFinal(data.copyOfRange(1 + length, data.size)), Charsets.UTF_8))
        return json.getString("ssid") to json.getString("password")
    }
    fun clear() = file.delete()
}
