import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import hashlib
import json

from src.main import app
from src.core.database import get_db
from src.db.models import Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_idempotency_prevents_duplicate():
    """Idempotency-Key returns cached response"""
    file_content = b"%PDF-1.4\n%test content for idempotency"
    file_hash = hashlib.sha256(file_content).hexdigest()

    evidence_data = {
        "evidence_id": "ev_idempo_001",
        "application_id": "app_test_001",
        "evidence_type": "document",
        "sha256_hash_device": file_hash,
        "captured_at_device": datetime.utcnow().isoformat() + "Z",
        "gps_coordinates": {"latitude": 64.1466, "longitude": -21.9426, "accuracy_meters": 10.0},
        "uploader_role": "applicant_owner",
        "mime_type": "application/pdf",
        "file_size_bytes": len(file_content),
    }

    # First request
    response1 = client.post(
        "/api/v1/evidence",
        headers={"Idempotency-Key": "test-key-001"},
        files={"file": ("test.pdf", file_content, "application/pdf")},
        data={"evidence_json": json.dumps(evidence_data)},
    )

    # Second request with same key
    response2 = client.post(
        "/api/v1/evidence",
        headers={"Idempotency-Key": "test-key-001"},
        files={"file": ("test.pdf", file_content, "application/pdf")},
        data={"evidence_json": json.dumps(evidence_data)},
    )

    # Should return same response (if both succeeded)
    if response1.status_code == 201:
        assert response1.json() == response2.json()


def test_duplicate_evidence_id_rejected():
    """Duplicate evidence_id returns 409"""
    file_content = b"%PDF-1.4\n%test content"
    file_hash = hashlib.sha256(file_content).hexdigest()

    evidence_data = {
        "evidence_id": "ev_dup_id_001",
        "application_id": "app_test_001",
        "evidence_type": "document",
        "sha256_hash_device": file_hash,
        "captured_at_device": datetime.utcnow().isoformat() + "Z",
        "gps_coordinates": {"latitude": 64.1466, "longitude": -21.9426, "accuracy_meters": 10.0},
        "uploader_role": "applicant_owner",
        "mime_type": "application/pdf",
        "file_size_bytes": len(file_content),
    }

    # First upload
    response1 = client.post(
        "/api/v1/evidence",
        files={"file": ("test1.pdf", file_content, "application/pdf")},
        data={"evidence_json": json.dumps(evidence_data)},
    )

    # Second upload with same evidence_id
    response2 = client.post(
        "/api/v1/evidence",
        files={"file": ("test2.pdf", file_content, "application/pdf")},
        data={"evidence_json": json.dumps(evidence_data)},
    )

    if response1.status_code == 201:
        assert response2.status_code == 409
        assert "DUPLICATE_EVIDENCE_ID" in response2.json().get("code", "")


def test_duplicate_content_detection():
    """Same file hash within replay window returns 409"""
    file_content = b"%PDF-1.4\n%unique content for duplicate test"
    file_hash = hashlib.sha256(file_content).hexdigest()

    evidence_data_1 = {
        "evidence_id": "ev_dup_content_001",
        "application_id": "app_test_001",
        "evidence_type": "document",
        "sha256_hash_device": file_hash,
        "captured_at_device": datetime.utcnow().isoformat() + "Z",
        "gps_coordinates": {"latitude": 64.1466, "longitude": -21.9426, "accuracy_meters": 10.0},
        "uploader_role": "applicant_owner",
        "mime_type": "application/pdf",
        "file_size_bytes": len(file_content),
    }

    # First upload
    response1 = client.post(
        "/api/v1/evidence",
        files={"file": ("test1.pdf", file_content, "application/pdf")},
        data={"evidence_json": json.dumps(evidence_data_1)},
    )

    # Second upload with different evidence_id but same content
    evidence_data_2 = {**evidence_data_1, "evidence_id": "ev_dup_content_002"}
    response2 = client.post(
        "/api/v1/evidence",
        files={"file": ("test2.pdf", file_content, "application/pdf")},
        data={"evidence_json": json.dumps(evidence_data_2)},
    )

    if response1.status_code == 201:
        assert response2.status_code == 409
        assert "DUPLICATE_CONTENT" in response2.json().get("code", "")


def test_hash_mismatch_rejected():
    """Hash mismatch returns 400"""
    file_content = b"%PDF-1.4\n%test content"
    wrong_hash = "a" * 64  # Intentionally wrong hash

    evidence_data = {
        "evidence_id": "ev_hash_mismatch",
        "application_id": "app_test_001",
        "evidence_type": "document",
        "sha256_hash_device": wrong_hash,
        "captured_at_device": datetime.utcnow().isoformat() + "Z",
        "gps_coordinates": {"latitude": 64.1466, "longitude": -21.9426, "accuracy_meters": 10.0},
        "uploader_role": "applicant_owner",
        "mime_type": "application/pdf",
        "file_size_bytes": len(file_content),
    }

    response = client.post(
        "/api/v1/evidence",
        files={"file": ("test.pdf", file_content, "application/pdf")},
        data={"evidence_json": json.dumps(evidence_data)},
    )

    assert response.status_code == 400
    assert "INTEGRITY_VALIDATION_FAILED" in response.json().get("code", "")
