package is.permia.core.models

import kotlinx.serialization.Serializable

@Serializable
data class EvidenceRecord(
    val evidenceId: String,
    val applicationId: String,
    val evidenceType: EvidenceType,
    val sha256HashDevice: String,
    val sha256HashServer: String? = null,
    val capturedAtDevice: String,
    val capturedAtServer: String? = null,
    val timeDriftSeconds: Double? = null,
    val gpsCoordinates: GpsCoordinates,
    val exifData: Map<String, String>? = null,
    val uploaderRole: UploaderRole,
    val storageUri: String? = null,
    val mimeType: String,
    val fileSizeBytes: Long,
    val uploadStatus: UploadStatus = UploadStatus.PENDING
)

@Serializable
enum class EvidenceType {
    PHOTO, VIDEO, DOCUMENT, AUDIO
}

@Serializable
data class GpsCoordinates(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Double
)

@Serializable
enum class UploaderRole {
    APPLICANT_OWNER, INSPECTOR, SUPERVISOR
}

@Serializable
enum class UploadStatus {
    PENDING, UPLOADING, COMPLETED, FAILED
}
