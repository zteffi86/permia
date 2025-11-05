from datetime import datetime, timezone
import magic
from ..schemas.evidence import EvidenceUploadRequest, IntegrityCheckResult
from ..core.config import settings
from ..core.mime_config import get_policy


class IntegrityService:
    """Service for validating evidence integrity"""

    def validate(
        self,
        evidence: EvidenceUploadRequest,
        server_hash: str,
        file_size: int,
        file_bytes: bytes,
        exif_data: dict,
    ) -> tuple[IntegrityCheckResult, str]:
        """
        Validate evidence integrity

        Returns:
            (IntegrityCheckResult, detected_mime)
        """
        issues: list[str] = []

        # Get policy for evidence type
        policy = get_policy(evidence.evidence_type.value)

        # 1. Hash verification
        hash_match = evidence.sha256_hash_device == server_hash
        if not hash_match:
            issues.append(
                f"Hash mismatch: device={evidence.sha256_hash_device[:16]}... "
                f"server={server_hash[:16]}..."
            )

        # 2. MIME type validation (server-sniffed vs policy)
        detected_mime = magic.from_buffer(file_bytes, mime=True)
        mime_valid = detected_mime in policy.allowed_mimes

        if not mime_valid:
            issues.append(
                f"MIME type not allowed for {evidence.evidence_type.value}: {detected_mime} "
                f"(allowed: {', '.join(policy.allowed_mimes)})"
            )

        if detected_mime != evidence.mime_type:
            issues.append(
                f"MIME mismatch: client={evidence.mime_type} server={detected_mime}"
            )

        # 3. File size check (per-type policy)
        max_size_bytes = policy.max_size_mb * 1024 * 1024
        file_size_ok = file_size <= max_size_bytes

        if not file_size_ok:
            issues.append(
                f"File exceeds {evidence.evidence_type.value} limit: "
                f"{file_size} bytes (max: {max_size_bytes})"
            )

        if file_size != evidence.file_size_bytes:
            issues.append(
                f"File size mismatch: claimed={evidence.file_size_bytes} actual={file_size}"
            )

        # 4. EXIF validation for photos
        exif_present = exif_data.get("has_exif", False)
        exif_ok = True

        if evidence.evidence_type == "photo":
            if not exif_present:
                exif_ok = False
                issues.append("EXIF data required for photos but not found")
            else:
                # Cross-check GPS if EXIF has GPS
                exif_gps_lat = exif_data.get("gps_latitude")
                exif_gps_lon = exif_data.get("gps_longitude")

                if exif_gps_lat is not None and exif_gps_lon is not None:
                    gps_diff_lat = abs(exif_gps_lat - evidence.gps_coordinates.latitude)
                    gps_diff_lon = abs(exif_gps_lon - evidence.gps_coordinates.longitude)

                    if gps_diff_lat > 0.001 or gps_diff_lon > 0.001:
                        issues.append(
                            f"GPS mismatch: EXIF ({exif_gps_lat:.6f}, {exif_gps_lon:.6f}) "
                            f"vs declared ({evidence.gps_coordinates.latitude:.6f}, "
                            f"{evidence.gps_coordinates.longitude:.6f})"
                        )

                # Cross-check datetime
                exif_dt = exif_data.get("datetime")
                if exif_dt:
                    device_time = evidence.captured_at_device
                    if device_time.tzinfo is None:
                        device_time = device_time.replace(tzinfo=timezone.utc)
                    elif exif_dt.tzinfo is None:
                        exif_dt = exif_dt.replace(tzinfo=timezone.utc)

                    time_diff = abs((exif_dt - device_time).total_seconds())
                    if time_diff > 60:
                        issues.append(
                            f"Timestamp mismatch: EXIF {exif_dt} vs declared {device_time}"
                        )

        # 5. GPS accuracy check
        gps_accuracy_ok = (
            evidence.gps_coordinates.accuracy_meters <= settings.MIN_GPS_ACCURACY_METERS
        )
        if not gps_accuracy_ok:
            issues.append(
                f"GPS accuracy insufficient: {evidence.gps_coordinates.accuracy_meters:.1f}m "
                f"(max: {settings.MIN_GPS_ACCURACY_METERS}m)"
            )

        # 6. Time drift check
        server_time = datetime.now(timezone.utc)
        device_time = evidence.captured_at_device
        if device_time.tzinfo is None:
            device_time = device_time.replace(tzinfo=timezone.utc)

        time_drift_seconds = abs((server_time - device_time).total_seconds())
        time_drift_ok = time_drift_seconds <= settings.MAX_TIME_DRIFT_SECONDS

        if not time_drift_ok:
            issues.append(
                f"Time drift excessive: {time_drift_seconds:.1f}s "
                f"(max: {settings.MAX_TIME_DRIFT_SECONDS}s)"
            )

        # Overall integrity
        integrity_passed = (
            hash_match
            and mime_valid
            and gps_accuracy_ok
            and time_drift_ok
            and file_size_ok
            and exif_ok
        )

        result = IntegrityCheckResult(
            hash_match=hash_match,
            exif_present=exif_present,
            gps_accuracy_ok=gps_accuracy_ok,
            time_drift_ok=time_drift_ok,
            file_size_ok=file_size_ok,
            integrity_passed=integrity_passed,
            issues=issues,
        )

        return (result, detected_mime)


# Singleton instance
integrity_service = IntegrityService()
