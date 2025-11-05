import pytest
from datetime import datetime, timezone, timedelta
from src.services.integrity_service import IntegrityService
from src.schemas.evidence import EvidenceUploadRequest, GpsCoordinates, EvidenceType, UploaderRole

integrity_service = IntegrityService()


def test_integrity_all_pass():
    """Test integrity validation success"""
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

    assert result.integrity_passed is True
    assert result.hash_match is True
    assert result.gps_accuracy_ok is True
    assert result.time_drift_ok is True
    assert len(result.issues) == 0


def test_integrity_hash_mismatch():
    """Test integrity failure on hash mismatch"""
    evidence = EvidenceUploadRequest(
        evidence_id="ev_test_002",
        application_id="app_test_001",
        evidence_type=EvidenceType.DOCUMENT,
        sha256_hash_device="b" * 64,
        captured_at_device=datetime.now(timezone.utc),
        gps_coordinates=GpsCoordinates(latitude=64.1466, longitude=-21.9426, accuracy_meters=10.0),
        uploader_role=UploaderRole.APPLICANT_OWNER,
        mime_type="application/pdf",
        file_size_bytes=1000,
    )

    file_bytes = b"%PDF-1.4\n%fake pdf content"
    server_hash = "a" * 64  # Different from device hash

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


def test_integrity_gps_accuracy_fail():
    """Test integrity failure on poor GPS accuracy"""
    evidence = EvidenceUploadRequest(
        evidence_id="ev_test_003",
        application_id="app_test_001",
        evidence_type=EvidenceType.DOCUMENT,
        sha256_hash_device="a" * 64,
        captured_at_device=datetime.now(timezone.utc),
        gps_coordinates=GpsCoordinates(latitude=64.1466, longitude=-21.9426, accuracy_meters=100.0),
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

    assert result.integrity_passed is False
    assert result.gps_accuracy_ok is False
    assert any("GPS accuracy" in issue for issue in result.issues)


def test_integrity_time_drift_fail():
    """Test integrity failure on excessive time drift"""
    past_time = datetime.now(timezone.utc) - timedelta(seconds=60)

    evidence = EvidenceUploadRequest(
        evidence_id="ev_test_004",
        application_id="app_test_001",
        evidence_type=EvidenceType.DOCUMENT,
        sha256_hash_device="a" * 64,
        captured_at_device=past_time,
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

    assert result.integrity_passed is False
    assert result.time_drift_ok is False
    assert any("Time drift" in issue for issue in result.issues)


def test_integrity_exif_required_for_photos():
    """Test that EXIF is required for photos"""
    evidence = EvidenceUploadRequest(
        evidence_id="ev_test_005",
        application_id="app_test_001",
        evidence_type=EvidenceType.PHOTO,
        sha256_hash_device="a" * 64,
        captured_at_device=datetime.now(timezone.utc),
        gps_coordinates=GpsCoordinates(latitude=64.1466, longitude=-21.9426, accuracy_meters=10.0),
        uploader_role=UploaderRole.APPLICANT_OWNER,
        mime_type="image/jpeg",
        file_size_bytes=1000,
    )

    file_bytes = b"\xff\xd8\xff\xe0fake jpeg"
    server_hash = "a" * 64

    result, detected_mime = integrity_service.validate(
        evidence=evidence,
        server_hash=server_hash,
        file_size=1000,
        file_bytes=file_bytes,
        exif_data={"has_exif": False},
    )

    assert result.integrity_passed is False
    assert result.exif_present is False
    assert any("EXIF" in issue for issue in result.issues)
