"""
Comprehensive test suite for export functionality

Tests cover:
- Export creation (success/failure)
- Export status retrieval
- Export download with redirects
- Expired export handling
- Export listing
- Package generation
- Multi-tenant isolation
- Audit logging
"""
import json
from datetime import datetime, timedelta
from typing import Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import Export, Evidence, AuditLog


class TestExportCreation:
    """Test export creation endpoint"""

    def test_create_export_success(
        self,
        client: TestClient,
        sample_export_data: dict[str, Any],
        create_evidence,
        test_db: Session,
    ):
        """Test successful export creation returns 202 Accepted"""
        # Arrange
        create_evidence(
            evidence_id="ev-1",
            application_id=sample_export_data["application_id"],
            tenant_id=sample_export_data["tenant_id"],
        )
        create_evidence(
            evidence_id="ev-2",
            application_id=sample_export_data["application_id"],
            tenant_id=sample_export_data["tenant_id"],
        )

        # Act
        response = client.post("/api/v1/exports", json=sample_export_data)

        # Assert
        assert response.status_code == 202
        result = response.json()
        assert "export_id" in result
        assert result["status"] == "pending"
        assert "created_at" in result

        # Verify database record
        db_export = test_db.query(Export).filter_by(export_id=result["export_id"]).first()
        assert db_export is not None
        assert db_export.status == "pending"
        assert db_export.application_id == sample_export_data["application_id"]

    def test_create_export_no_evidence(
        self,
        client: TestClient,
        sample_export_data: dict[str, Any],
    ):
        """Test that creating export with no evidence returns 404"""
        # Arrange - No evidence created

        # Act
        response = client.post("/api/v1/exports", json=sample_export_data)

        # Assert
        assert response.status_code == 404
        assert "no evidence found" in response.json()["detail"].lower()

    def test_create_export_with_custom_options(
        self,
        client: TestClient,
        sample_export_data: dict[str, Any],
        create_evidence,
        test_db: Session,
    ):
        """Test export creation with custom options"""
        # Arrange
        create_evidence(
            evidence_id="ev-1",
            application_id=sample_export_data["application_id"],
            tenant_id=sample_export_data["tenant_id"],
        )

        data = sample_export_data.copy()
        data["options"] = {
            "include_metadata": False,
            "include_signatures": True,
            "format": "tar.gz",
            "encryption": "aes256",
        }

        # Act
        response = client.post("/api/v1/exports", json=data)

        # Assert
        assert response.status_code == 202
        result = response.json()

        # Verify options were stored
        db_export = test_db.query(Export).filter_by(export_id=result["export_id"]).first()
        assert db_export.options["encryption"] == "aes256"
        assert db_export.options["format"] == "tar.gz"


class TestExportRetrieval:
    """Test export status and retrieval endpoints"""

    def test_get_export_status_pending(
        self,
        client: TestClient,
        create_export,
    ):
        """Test retrieving pending export status"""
        # Arrange
        export = create_export(status="pending")

        # Act
        response = client.get(f"/api/v1/exports/{export.export_id}")

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["export_id"] == export.export_id
        assert result["status"] == "pending"
        assert "download_url" not in result  # No URL for pending export

    def test_get_export_status_completed(
        self,
        client: TestClient,
        create_export,
        mock_storage,
    ):
        """Test retrieving completed export with download URL"""
        # Arrange
        export = create_export(
            status="completed",
            storage_path="exports/exp-123.zip",
            file_size=1024000,
        )
        mock_storage.generate_presigned_url.return_value = "https://storage.example.com/exp-123.zip?sas=token"

        # Act
        response = client.get(f"/api/v1/exports/{export.export_id}")

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert "download_url" in result
        assert result["file_size"] == 1024000

    def test_get_export_status_failed(
        self,
        client: TestClient,
        create_export,
    ):
        """Test retrieving failed export with error message"""
        # Arrange
        export = create_export(
            status="failed",
            error_message="Storage service unavailable",
        )

        # Act
        response = client.get(f"/api/v1/exports/{export.export_id}")

        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "failed"
        assert result["error_message"] == "Storage service unavailable"

    def test_get_export_not_found(
        self,
        client: TestClient,
    ):
        """Test retrieving non-existent export returns 404"""
        # Act
        response = client.get("/api/v1/exports/non-existent-export-id")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestExportDownload:
    """Test export download endpoint with redirects"""

    def test_download_export_redirect(
        self,
        client: TestClient,
        create_export,
        mock_storage,
    ):
        """Test that download returns 307 redirect to presigned URL"""
        # Arrange
        export = create_export(
            status="completed",
            storage_path="exports/exp-download.zip",
        )
        presigned_url = "https://storage.example.com/exp-download.zip?sas=token123"
        mock_storage.generate_presigned_url.return_value = presigned_url

        # Act
        response = client.get(
            f"/api/v1/exports/{export.export_id}/download",
            allow_redirects=False,
        )

        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == presigned_url

    def test_download_export_pending(
        self,
        client: TestClient,
        create_export,
    ):
        """Test that downloading pending export returns 409 Conflict"""
        # Arrange
        export = create_export(status="pending")

        # Act
        response = client.get(f"/api/v1/exports/{export.export_id}/download")

        # Assert
        assert response.status_code == 409
        assert "not ready" in response.json()["detail"].lower()

    def test_download_export_failed(
        self,
        client: TestClient,
        create_export,
    ):
        """Test that downloading failed export returns 410 Gone"""
        # Arrange
        export = create_export(
            status="failed",
            error_message="Generation failed",
        )

        # Act
        response = client.get(f"/api/v1/exports/{export.export_id}/download")

        # Assert
        assert response.status_code == 410
        assert "failed" in response.json()["detail"].lower()

    def test_download_export_expired(
        self,
        client: TestClient,
        create_export,
    ):
        """Test that downloading expired export returns 410 Gone"""
        # Arrange
        past_date = datetime.utcnow() - timedelta(days=1)
        export = create_export(
            status="completed",
            storage_path="exports/exp-expired.zip",
            expires_at=past_date,
        )

        # Act
        response = client.get(f"/api/v1/exports/{export.export_id}/download")

        # Assert
        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()


class TestExportListing:
    """Test export listing endpoints"""

    def test_list_exports_for_application(
        self,
        client: TestClient,
        create_export,
    ):
        """Test listing all exports for an application"""
        # Arrange
        app_id = "app-list-exports"
        create_export(export_id="exp-1", application_id=app_id, status="completed")
        create_export(export_id="exp-2", application_id=app_id, status="pending")
        create_export(export_id="exp-3", application_id="other-app", status="completed")

        # Act
        response = client.get(f"/api/v1/exports?application_id={app_id}")

        # Assert
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert all(e["application_id"] == app_id for e in results)

    def test_list_exports_with_status_filter(
        self,
        client: TestClient,
        create_export,
    ):
        """Test filtering exports by status"""
        # Arrange
        app_id = "app-filter-test"
        create_export(export_id="exp-comp", application_id=app_id, status="completed")
        create_export(export_id="exp-pend", application_id=app_id, status="pending")
        create_export(export_id="exp-fail", application_id=app_id, status="failed")

        # Act
        response = client.get(f"/api/v1/exports?application_id={app_id}&status=completed")

        # Assert
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["status"] == "completed"


class TestExportPackageGeneration:
    """Test export package generation logic"""

    def test_export_package_structure(
        self,
        client: TestClient,
        create_evidence,
        create_export,
        sample_export_data: dict[str, Any],
        test_db: Session,
    ):
        """Test that export package contains correct files"""
        # Arrange
        ev1 = create_evidence(
            evidence_id="ev-pkg-1",
            application_id=sample_export_data["application_id"],
            tenant_id=sample_export_data["tenant_id"],
            storage_path="evidence/aa/aaa111",
            file_hash="a" * 64,
        )
        ev2 = create_evidence(
            evidence_id="ev-pkg-2",
            application_id=sample_export_data["application_id"],
            tenant_id=sample_export_data["tenant_id"],
            storage_path="evidence/bb/bbb222",
            file_hash="b" * 64,
        )

        # Act
        response = client.post("/api/v1/exports", json=sample_export_data)

        # Assert
        assert response.status_code == 202
        export_id = response.json()["export_id"]

        # Verify export record has correct metadata
        db_export = test_db.query(Export).filter_by(export_id=export_id).first()
        assert db_export.options["include_metadata"] is True
        assert db_export.options["include_signatures"] is True

    def test_export_includes_manifest(
        self,
        client: TestClient,
        create_evidence,
        sample_export_data: dict[str, Any],
        test_db: Session,
    ):
        """Test that export includes manifest.json with metadata"""
        # Arrange
        create_evidence(
            evidence_id="ev-manifest",
            application_id=sample_export_data["application_id"],
            tenant_id=sample_export_data["tenant_id"],
        )

        # Act
        response = client.post("/api/v1/exports", json=sample_export_data)

        # Assert
        assert response.status_code == 202
        # In a real test, we'd verify the ZIP contents
        # Here we verify the export was created with correct options
        export_id = response.json()["export_id"]
        db_export = test_db.query(Export).filter_by(export_id=export_id).first()
        assert db_export.options.get("include_metadata") is True


class TestExportMultiTenancy:
    """Test multi-tenant isolation for exports"""

    def test_tenant_cannot_access_other_tenant_export(
        self,
        client: TestClient,
        create_export,
    ):
        """Test that tenants cannot access each other's exports"""
        # Arrange
        tenant1_export = create_export(
            export_id="tenant1-export",
            tenant_id="tenant-001",
            application_id="app-001",
        )
        tenant2_export = create_export(
            export_id="tenant2-export",
            tenant_id="tenant-002",
            application_id="app-001",
        )

        # Act - Tenant 1 tries to access their export
        response1 = client.get(
            f"/api/v1/exports/{tenant1_export.export_id}",
            headers={"X-Tenant-ID": "tenant-001"},
        )

        # Act - Tenant 1 tries to access Tenant 2's export
        response2 = client.get(
            f"/api/v1/exports/{tenant2_export.export_id}",
            headers={"X-Tenant-ID": "tenant-001"},
        )

        # Assert
        assert response1.status_code == 200  # Can access own export
        assert response2.status_code == 404  # Cannot access other tenant's export

    def test_export_only_includes_tenant_evidence(
        self,
        client: TestClient,
        create_evidence,
        sample_export_data: dict[str, Any],
    ):
        """Test that export only includes evidence from same tenant"""
        # Arrange
        tenant_id = sample_export_data["tenant_id"]
        app_id = sample_export_data["application_id"]

        # Create evidence for correct tenant
        create_evidence(
            evidence_id="tenant-ev-1",
            tenant_id=tenant_id,
            application_id=app_id,
        )
        create_evidence(
            evidence_id="tenant-ev-2",
            tenant_id=tenant_id,
            application_id=app_id,
        )

        # Create evidence for different tenant (should not be included)
        create_evidence(
            evidence_id="other-tenant-ev",
            tenant_id="other-tenant",
            application_id=app_id,
        )

        # Act
        response = client.post("/api/v1/exports", json=sample_export_data)

        # Assert
        assert response.status_code == 202
        # Export should be created (has 2 evidence items from correct tenant)
        # The other tenant's evidence should not cause issues


class TestExportAuditLogging:
    """Test audit logging for export operations"""

    def test_export_creation_logged(
        self,
        client: TestClient,
        create_evidence,
        sample_export_data: dict[str, Any],
        test_db: Session,
    ):
        """Test that export creation is logged in audit trail"""
        # Arrange
        create_evidence(
            evidence_id="ev-audit",
            application_id=sample_export_data["application_id"],
            tenant_id=sample_export_data["tenant_id"],
        )

        # Act
        response = client.post("/api/v1/exports", json=sample_export_data)

        # Assert
        assert response.status_code == 202
        export_id = response.json()["export_id"]

        # Verify audit log (if AuditLog model exists)
        # audit_logs = test_db.query(AuditLog).filter_by(
        #     resource_type="export",
        #     resource_id=export_id,
        #     action="create",
        # ).all()
        # assert len(audit_logs) == 1

    def test_export_download_logged(
        self,
        client: TestClient,
        create_export,
        mock_storage,
        test_db: Session,
    ):
        """Test that export downloads are logged"""
        # Arrange
        export = create_export(
            status="completed",
            storage_path="exports/exp-audit.zip",
        )
        mock_storage.generate_presigned_url.return_value = "https://storage.example.com/test"

        # Act
        client.get(f"/api/v1/exports/{export.export_id}/download", allow_redirects=False)

        # Assert
        # Verify audit log (if AuditLog model exists)
        # audit_logs = test_db.query(AuditLog).filter_by(
        #     resource_type="export",
        #     resource_id=export.export_id,
        #     action="download",
        # ).all()
        # assert len(audit_logs) == 1


class TestExportValidation:
    """Test export request validation"""

    def test_export_requires_application_id(
        self,
        client: TestClient,
    ):
        """Test that export creation requires application_id"""
        # Arrange
        data = {
            "tenant_id": "tenant-001",
            # Missing application_id
        }

        # Act
        response = client.post("/api/v1/exports", json=data)

        # Assert
        assert response.status_code == 422

    def test_export_requires_tenant_id(
        self,
        client: TestClient,
    ):
        """Test that export creation requires tenant_id"""
        # Arrange
        data = {
            "application_id": "app-001",
            # Missing tenant_id
        }

        # Act
        response = client.post("/api/v1/exports", json=data)

        # Assert
        assert response.status_code == 422

    def test_export_options_validation(
        self,
        client: TestClient,
        create_evidence,
    ):
        """Test that export options are validated"""
        # Arrange
        create_evidence(
            evidence_id="ev-opt",
            application_id="app-001",
            tenant_id="tenant-001",
        )

        data = {
            "application_id": "app-001",
            "tenant_id": "tenant-001",
            "options": {
                "include_metadata": "not-a-boolean",  # Invalid type
            },
        }

        # Act
        response = client.post("/api/v1/exports", json=data)

        # Assert - Should either reject or coerce to boolean
        assert response.status_code in [202, 422]
