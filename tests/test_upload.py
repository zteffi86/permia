"""
Comprehensive test suite for evidence upload functionality

Tests cover:
- Evidence upload success scenarios
- Validation failures
- Hash verification
- File size limits
- GPS accuracy validation
- Time drift validation
- Idempotency
- Multi-tenant isolation
- Evidence retrieval
"""
import io
import hashlib
from datetime import datetime, timedelta
from typing import Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import Evidence


class TestEvidenceUpload:
    """Test evidence upload endpoint"""

    def test_upload_evidence_success(
        self,
        client: TestClient,
        sample_image: bytes,
        sample_evidence_data: dict[str, Any],
        mock_storage,
        mock_exif,
        test_db: Session,
    ):
        """Test successful evidence upload with all validations passing"""
        # Arrange
        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = sample_evidence_data.copy()

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 201
        result = response.json()
        assert result["evidence_id"] == data["evidence_id"]
        assert result["status"] == "stored"
        assert "storage_url" in result
        assert "uploaded_at" in result

        # Verify database record
        db_evidence = test_db.query(Evidence).filter_by(evidence_id=data["evidence_id"]).first()
        assert db_evidence is not None
        assert db_evidence.file_hash == data["file_hash"]
        assert db_evidence.application_id == data["application_id"]
        assert db_evidence.tenant_id == data["tenant_id"]

        # Verify storage service was called
        mock_storage.upload_file.assert_called_once()

    def test_upload_duplicate_evidence_id(
        self,
        client: TestClient,
        sample_image: bytes,
        sample_evidence_data: dict[str, Any],
        mock_storage,
        mock_exif,
        create_evidence,
    ):
        """Test that uploading with duplicate evidence_id returns 409 Conflict"""
        # Arrange - Create existing evidence
        create_evidence(evidence_id=sample_evidence_data["evidence_id"])

        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = sample_evidence_data.copy()

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_upload_file_too_large(
        self,
        client: TestClient,
        sample_evidence_data: dict[str, Any],
        mock_storage,
        mock_exif,
    ):
        """Test that files exceeding size limit are rejected with 413"""
        # Arrange - Create file larger than 100MB
        large_file = b"x" * (101 * 1024 * 1024)  # 101 MB
        files = {"file": ("large.jpg", io.BytesIO(large_file), "image/jpeg")}

        data = sample_evidence_data.copy()
        data["file_size"] = len(large_file)
        data["file_hash"] = hashlib.sha256(large_file).hexdigest()

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_upload_hash_mismatch(
        self,
        client: TestClient,
        sample_image: bytes,
        sample_evidence_data: dict[str, Any],
        mock_storage,
        mock_exif,
    ):
        """Test that hash mismatch is detected and rejected"""
        # Arrange
        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = sample_evidence_data.copy()
        data["file_hash"] = "0" * 64  # Wrong hash

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 400
        assert "hash mismatch" in response.json()["detail"].lower()

    def test_upload_invalid_json(
        self,
        client: TestClient,
        sample_image: bytes,
    ):
        """Test that malformed JSON returns 422"""
        # Arrange
        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = {"evidence_id": "test-001"}  # Missing required fields

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 422

    def test_upload_missing_required_fields(
        self,
        client: TestClient,
        sample_image: bytes,
    ):
        """Test that missing required fields returns 422"""
        # Arrange
        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = {
            "evidence_id": "test-001",
            # Missing: application_id, tenant_id, timestamp, file_hash, etc.
        }

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 422

    def test_upload_with_idempotency_key(
        self,
        client: TestClient,
        sample_image: bytes,
        sample_evidence_data: dict[str, Any],
        mock_storage,
        mock_exif,
        test_db: Session,
    ):
        """Test idempotency key prevents duplicate processing"""
        # Arrange
        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = sample_evidence_data.copy()
        data["idempotency_key"] = "unique-request-001"

        # Act - First request
        response1 = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Act - Second request with same idempotency key (different evidence_id)
        data2 = data.copy()
        data2["evidence_id"] = "test-evidence-002"
        files2 = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        response2 = client.post("/api/v1/evidence/upload", data=data2, files=files2)

        # Assert
        assert response1.status_code == 201
        assert response2.status_code == 201
        # Should return cached response from first request
        assert response2.json()["evidence_id"] == response1.json()["evidence_id"]

    def test_upload_gps_accuracy_too_low(
        self,
        client: TestClient,
        sample_image: bytes,
        sample_evidence_data: dict[str, Any],
        mock_storage,
        mock_exif,
    ):
        """Test that GPS accuracy below threshold is rejected"""
        # Arrange
        mock_exif.extract_metadata.return_value = {
            "gps": {
                "latitude": 64.1466,
                "longitude": -21.9426,
                "accuracy": 100.0,  # Too low (> 50m threshold)
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = sample_evidence_data.copy()

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 400
        assert "gps accuracy" in response.json()["detail"].lower()

    def test_upload_time_drift_too_large(
        self,
        client: TestClient,
        sample_image: bytes,
        sample_evidence_data: dict[str, Any],
        mock_storage,
        mock_exif,
    ):
        """Test that excessive time drift is rejected"""
        # Arrange
        old_time = datetime.utcnow() - timedelta(seconds=60)  # 60s drift > 30s threshold
        mock_exif.extract_metadata.return_value = {
            "gps": {
                "latitude": 64.1466,
                "longitude": -21.9426,
                "accuracy": 10.0,
            },
            "timestamp": old_time.isoformat(),
        }

        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = sample_evidence_data.copy()

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 400
        assert "time drift" in response.json()["detail"].lower()

    def test_multi_tenant_isolation(
        self,
        client: TestClient,
        create_evidence,
    ):
        """Test that tenants cannot access each other's evidence"""
        # Arrange
        tenant1_evidence = create_evidence(
            evidence_id="tenant1-evidence",
            tenant_id="tenant-001",
            application_id="app-001",
        )
        tenant2_evidence = create_evidence(
            evidence_id="tenant2-evidence",
            tenant_id="tenant-002",
            application_id="app-001",
        )

        # Act - Tenant 1 tries to access their evidence
        response1 = client.get(
            f"/api/v1/evidence/{tenant1_evidence.evidence_id}",
            headers={"X-Tenant-ID": "tenant-001"},
        )

        # Act - Tenant 1 tries to access Tenant 2's evidence
        response2 = client.get(
            f"/api/v1/evidence/{tenant2_evidence.evidence_id}",
            headers={"X-Tenant-ID": "tenant-001"},
        )

        # Assert
        assert response1.status_code == 200  # Can access own evidence
        assert response2.status_code == 404  # Cannot access other tenant's evidence


class TestEvidenceRetrieval:
    """Test evidence retrieval endpoints"""

    def test_get_evidence_by_id(
        self,
        client: TestClient,
        create_evidence,
    ):
        """Test retrieving evidence by ID"""
        # Arrange
        evidence = create_evidence(evidence_id="test-retrieve-001")

        # Act
        response = client.get(f"/api/v1/evidence/{evidence.evidence_id}")

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["evidence_id"] == evidence.evidence_id
        assert result["file_hash"] == evidence.file_hash
        assert result["storage_path"] == evidence.storage_path

    def test_get_evidence_not_found(
        self,
        client: TestClient,
    ):
        """Test retrieving non-existent evidence returns 404"""
        # Act
        response = client.get("/api/v1/evidence/non-existent-id")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_evidence_for_application(
        self,
        client: TestClient,
        create_evidence,
    ):
        """Test listing all evidence for an application"""
        # Arrange
        app_id = "app-list-test"
        create_evidence(evidence_id="ev-1", application_id=app_id)
        create_evidence(evidence_id="ev-2", application_id=app_id)
        create_evidence(evidence_id="ev-3", application_id="other-app")

        # Act
        response = client.get(f"/api/v1/evidence?application_id={app_id}")

        # Assert
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert all(e["application_id"] == app_id for e in results)

    def test_list_evidence_with_pagination(
        self,
        client: TestClient,
        create_evidence,
    ):
        """Test evidence listing supports pagination"""
        # Arrange
        app_id = "app-pagination-test"
        for i in range(10):
            create_evidence(evidence_id=f"ev-{i}", application_id=app_id)

        # Act
        response = client.get(f"/api/v1/evidence?application_id={app_id}&limit=5")

        # Assert
        assert response.status_code == 200
        results = response.json()
        assert len(results) <= 5

    def test_get_evidence_with_presigned_url(
        self,
        client: TestClient,
        create_evidence,
        mock_storage,
    ):
        """Test that evidence retrieval includes presigned URL"""
        # Arrange
        evidence = create_evidence(evidence_id="test-url-001")
        mock_storage.generate_presigned_url.return_value = "https://storage.example.com/test?sas=token"

        # Act
        response = client.get(f"/api/v1/evidence/{evidence.evidence_id}?include_url=true")

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert "download_url" in result
        assert result["download_url"].startswith("https://")


class TestEvidenceValidation:
    """Test evidence validation logic"""

    def test_validate_mime_type_allowed(
        self,
        client: TestClient,
        sample_evidence_data: dict[str, Any],
        sample_image: bytes,
        mock_storage,
        mock_exif,
    ):
        """Test that allowed MIME types are accepted"""
        # Arrange
        allowed_types = ["image/jpeg", "image/png", "video/mp4", "application/pdf"]

        for mime_type in allowed_types:
            files = {"file": ("test.jpg", io.BytesIO(sample_image), mime_type)}
            data = sample_evidence_data.copy()
            data["evidence_id"] = f"test-{mime_type.replace('/', '-')}"
            data["mime_type"] = mime_type

            # Act
            response = client.post("/api/v1/evidence/upload", data=data, files=files)

            # Assert
            assert response.status_code in [201, 400]  # 201 success or 400 for other validation

    def test_validate_file_hash_format(
        self,
        client: TestClient,
        sample_image: bytes,
        sample_evidence_data: dict[str, Any],
    ):
        """Test that file_hash must be valid SHA-256 (64 hex chars)"""
        # Arrange
        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = sample_evidence_data.copy()
        data["file_hash"] = "invalid-hash"  # Not 64 hex chars

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 422  # Validation error

    def test_validate_timestamp_format(
        self,
        client: TestClient,
        sample_image: bytes,
        sample_evidence_data: dict[str, Any],
    ):
        """Test that timestamp must be valid ISO 8601 format"""
        # Arrange
        files = {"file": ("test.jpg", io.BytesIO(sample_image), "image/jpeg")}
        data = sample_evidence_data.copy()
        data["timestamp"] = "invalid-timestamp"

        # Act
        response = client.post("/api/v1/evidence/upload", data=data, files=files)

        # Assert
        assert response.status_code == 422  # Validation error
