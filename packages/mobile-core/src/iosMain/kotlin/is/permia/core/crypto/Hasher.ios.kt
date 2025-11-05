package is.permia.core.crypto

import kotlinx.cinterop.*
import platform.Foundation.*
import platform.Security.*

actual object Hasher {
    actual suspend fun sha256(filePath: String): String {
        val fileData = NSData.dataWithContentsOfFile(filePath)
            ?: throw IllegalArgumentException("File not found: $filePath")

        return sha256(fileData.bytes?.readBytes(fileData.length.toInt()) ?: byteArrayOf())
    }

    actual fun sha256(data: ByteArray): String {
        val digest = UByteArray(Int.SIZE_BYTES * 8)

        data.usePinned { pinned ->
            CC_SHA256(pinned.addressOf(0), data.size.toUInt(), digest.refTo(0))
        }

        return digest.joinToString("") { "%02x".format(it.toByte()) }
    }
}

@OptIn(ExperimentalForeignApi::class)
private external fun CC_SHA256(
    data: CValuesRef<ByteVar>?,
    len: UInt,
    md: CValuesRef<UByteVar>?
): CValuesRef<UByteVar>?
