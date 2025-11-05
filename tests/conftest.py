"""
Pytest configuration and fixtures for comprehensive test suite
"""
import io
import os
import pytest
import hashlib
from datetime import datetime, timedelta
from typing import Generator, Any
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from PIL import Image

from src.db.models import Base, Evidence, Export
from src.core.database import get_db
from src.core.rate_limit import rate_limiter
from src.main import app


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Create an in-memory SQLite database for testing

    Each test gets a fresh database with all tables created.
    Automatically cleans up after the test.
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    Create FastAPI test client with dependency overrides

    Overrides:
    - Database session (uses test_db)
    - Storage service (uses mock)
    - EXIF extractor (uses mock)
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# STORAGE SERVICE MOCKS
# ============================================================================

@pytest.fixture(scope="function")
def mock_storage():
    """
    Mock Azure Blob Storage service

    Simulates:
    - File uploads with hash-based paths
    - Presigned URL generation
    - File deletion
    - Health checks
    """
    with patch("src.services.storage.storage_service") as mock:
        # Configure mock methods
        mock.upload_file = Mock(return_value="evidence/ab/abc123...")
        mock.delete_file = Mock()
        mock.compute_hash_streaming = Mock(side_effect=lambda b: hashlib.sha256(b).hexdigest())
        mock.generate_presigned_url = Mock(
            return_value="https://storage.example.com/evidence/abc123?sas=token"
        )
        mock.check_health = Mock(return_value=True)

        yield mock


@pytest.fixture(scope="function")
def mock_exif():
    """
    Mock EXIF metadata extractor

    Returns realistic GPS and timestamp data for test images
    """
    with patch("src.services.exif_extractor.ExifExtractor") as MockExtractor:
        instance = MockExtractor.return_value
        instance.extract_metadata.return_value = {
            "gps": {
                "latitude": 64.1466,
                "longitude": -21.9426,
                "accuracy": 10.0,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        yield instance


# ============================================================================
# TEST DATA GENERATORS
# ============================================================================

@pytest.fixture
def sample_image() -> bytes:
    """
    Generate a valid JPEG image for testing

    Returns 1x1 pixel RGB JPEG (minimal valid image)
    """
    img = Image.new("RGB", (1, 1), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def sample_evidence_data(sample_image: bytes) -> dict[str, Any]:
    """
    Create valid evidence upload request data

    Includes all required fields with realistic values
    """
    file_hash = hashlib.sha256(sample_image).hexdigest()

    return {
        "evidence_id": "test-evidence-001",
        "application_id": "app-test-001",
        "tenant_id": "tenant-test-001",
        "timestamp": datetime.utcnow().isoformat(),
        "file_hash": file_hash,
        "file_size": len(sample_image),
        "mime_type": "image/jpeg",
        "metadata": {
            "gps": {
                "latitude": 64.1466,
                "longitude": -21.9426,
                "accuracy": 10.0,
            },
            "device_id": "device-test-001",
            "app_version": "1.0.0",
        },
    }


@pytest.fixture
def sample_export_data() -> dict[str, Any]:
    """
    Create valid export request data
    """
    return {
        "application_id": "app-test-001",
        "tenant_id": "tenant-test-001",
        "options": {
            "include_metadata": True,
            "include_signatures": True,
            "format": "zip",
        },
    }


# ============================================================================
# DATABASE FACTORY FIXTURES
# ============================================================================

@pytest.fixture
def create_evidence(test_db: Session):
    """
    Factory fixture for creating Evidence records

    Usage:
        evidence = create_evidence(evidence_id="test-001", ...)
    """
    def _create_evidence(**kwargs) -> Evidence:
        defaults = {
            "evidence_id": "test-evidence-001",
            "application_id": "app-test-001",
            "tenant_id": "tenant-test-001",
            "storage_path": "evidence/ab/abc123",
            "file_hash": "abc123" * 10 + "abcd",  # 64 char hex
            "file_size": 1024,
            "mime_type": "image/jpeg",
            "timestamp": datetime.utcnow(),
            "metadata": {
                "gps": {"latitude": 64.1466, "longitude": -21.9426, "accuracy": 10.0},
                "device_id": "device-001",
            },
            "idempotency_key": None,
        }
        defaults.update(kwargs)

        evidence = Evidence(**defaults)
        test_db.add(evidence)
        test_db.commit()
        test_db.refresh(evidence)
        return evidence

    return _create_evidence


@pytest.fixture
def create_export(test_db: Session):
    """
    Factory fixture for creating Export records

    Usage:
        export = create_export(export_id="exp-001", status="pending", ...)
    """
    def _create_export(**kwargs) -> Export:
        defaults = {
            "export_id": f"exp-{datetime.utcnow().timestamp()}",
            "application_id": "app-test-001",
            "tenant_id": "tenant-test-001",
            "status": "pending",
            "storage_path": None,
            "file_size": None,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=7),
            "options": {"include_metadata": True},
            "error_message": None,
        }
        defaults.update(kwargs)

        export = Export(**defaults)
        test_db.add(export)
        test_db.commit()
        test_db.refresh(export)
        return export

    return _create_export


# ============================================================================
# RATE LIMITER FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Automatically reset rate limiter before each test

    Ensures tests don't interfere with each other
    """
    rate_limiter.reset_all()
    yield
    rate_limiter.reset_all()


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def auth_headers() -> dict[str, str]:
    """
    Generate valid authentication headers for testing

    For now, returns empty dict since AUTH_REQUIRED=False in dev
    In production tests, this would generate JWT tokens
    """
    return {}


@pytest.fixture
def tenant_context() -> dict[str, str]:
    """
    Provide tenant context for multi-tenant testing
    """
    return {
        "tenant_id": "tenant-test-001",
        "application_id": "app-test-001",
    }


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def freeze_time():
    """
    Mock datetime for time-sensitive tests

    Usage:
        with freeze_time("2025-01-01T00:00:00Z"):
            # Your test code
    """
    from unittest.mock import patch
    from datetime import datetime

    def _freeze(frozen_time: str):
        frozen_dt = datetime.fromisoformat(frozen_time.replace("Z", "+00:00"))
        return patch("datetime.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = frozen_dt
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            yield mock_datetime

    return _freeze


@pytest.fixture
def clean_db(test_db: Session):
    """
    Clean all data from test database

    Useful for tests that need a completely fresh state
    """
    def _clean():
        test_db.query(Export).delete()
        test_db.query(Evidence).delete()
        test_db.commit()

    return _clean


# ============================================================================
# CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """
    Pytest configuration hook

    Sets environment variables and test markers
    """
    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA=="
    os.environ["AZURE_STORAGE_CONTAINER_NAME"] = "test-evidence"
    os.environ["AZURE_STORAGE_EXPORT_CONTAINER_NAME"] = "test-exports"
    os.environ["AUTH_REQUIRED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "true"
    os.environ["RATE_LIMIT_PER_MINUTE"] = "60"

    # Register custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
