package is.permia.core.crypto

import java.io.File
import java.io.FileInputStream
import java.security.MessageDigest

actual object Hasher {
    actual suspend fun sha256(filePath: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val file = File(filePath)

        FileInputStream(file).use { fis ->
            val buffer = ByteArray(8192)
            var bytesRead: Int
            while (fis.read(buffer).also { bytesRead = it } != -1) {
                digest.update(buffer, 0, bytesRead)
            }
        }

        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    actual fun sha256(data: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(data).joinToString("") { "%02x".format(it) }
    }
}
