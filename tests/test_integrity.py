import pytest
from datetime import datetime, timezone, timedelta
from src.services.integrity import integrity_service
from src.schemas.evidence import (
    EvidenceUploadRequest,
    EvidenceType,
    UploaderRole,
    GpsCoordinates,
)


def test_integrity_pass():
    """Test successful integrity validation"""
    evidence = EvidenceUploadRequest(
        evidence_id="ev_test_001",
        application_id="app_test_001",
        evidence_type=EvidenceType.DOCUMENT,
        sha256_hash_device="a" * 64,
        captured_at_device=datetime.now(timezone.utc),
        gps_coordinates=GpsCoordinates(latitude=64.1466, longitude=-21.9426, accuracy_meters=10.0),
        uploader_role=UploaderRole.APPLICANT_OWNER,
        mime_type="application/pdf",
        file_size_bytes=1000,
    )

    file_bytes = b"%PDF-1.4\n%fake pdf content"
    server_hash = "a" * 64

    result, detected_mime = integrity_service.validate(
        evidence=evidence,
        server_hash=server_hash,
        file_size=1000,
        file_bytes=file_bytes,
        exif_data={},
    )

    assert result.hash_match is True
    assert result.file_size_ok is True


def test_integrity_hash_mismatch():
    """Test integrity failure on hash mismatch"""
    evidence = EvidenceUploadRequest(
        evidence_id="ev_test_002",
        application_id="app_test_001",
        evidence_type=EvidenceType.DOCUMENT,
        sha256_hash_device="a" * 64,
        captured_at_device=datetime.now(timezone.utc),
        gps_coordinates=GpsCoordinates(latitude=64.1466, longitude=-21.9426, accuracy_meters=10.0),
        uploader_role=UploaderRole.APPLICANT_OWNER,
        mime_type="application/pdf",
        file_size_bytes=1000,
    )

    file_bytes = b"%PDF-1.4\n%fake pdf content"
    server_hash = "b" * 64

    result, detected_mime = integrity_service.validate(
        evidence=evidence,
        server_hash=server_hash,
        file_size=1000,
        file_bytes=file_bytes,
        exif_data={},
    )

    assert result.integrity_passed is False
    assert result.hash_match is False
    assert any("Hash mismatch" in issue for issue in result.issues)
