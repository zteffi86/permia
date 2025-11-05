package is.permia.core.crypto

expect object Hasher {
    suspend fun sha256(filePath: String): String
    fun sha256(data: ByteArray): String
}
