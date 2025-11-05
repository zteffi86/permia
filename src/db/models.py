from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, Text, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Evidence(Base):
    """Evidence table for storing uploaded evidence records"""

    __tablename__ = "evidence"

    # Primary identifiers
    evidence_id = Column(String, primary_key=True)
    application_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Evidence metadata
    evidence_type = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    mime_type_detected = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)

    # Hash verification
    sha256_hash_device = Column(String(64), nullable=False)
    sha256_hash_server = Column(String(64), nullable=False, index=True)

    # Timestamps
    captured_at_device = Column(DateTime, nullable=False)
    captured_at_server = Column(DateTime, nullable=False)
    time_drift_seconds = Column(Float, nullable=False)

    # GPS data
    gps_latitude = Column(Float, nullable=False)
    gps_longitude = Column(Float, nullable=False)
    gps_accuracy_meters = Column(Float, nullable=False)

    # EXIF metadata (server-extracted)
    exif_present = Column(Boolean, nullable=False, default=False)
    exif_data = Column(JSON, nullable=True)
    exif_gps_latitude = Column(Float, nullable=True)
    exif_gps_longitude = Column(Float, nullable=True)
    exif_datetime = Column(DateTime, nullable=True)

    # Uploader (from JWT, NOT client payload)
    uploader_role = Column(String, nullable=False)
    uploader_id = Column(String, nullable=False)

    # Storage (hash-based path)
    storage_path = Column(String, nullable=False)

    # Integrity validation
    integrity_passed = Column(Boolean, nullable=False, default=False)
    integrity_issues = Column(JSON, nullable=True)

    # Audit
    correlation_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_evidence_tenant_app", "tenant_id", "application_id"),
        Index("ix_evidence_app_created", "application_id", "created_at"),
        Index("ix_evidence_hash_created", "sha256_hash_server", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Evidence(id={self.evidence_id}, app={self.application_id})>"


class AuditLog(Base):
    """Append-only audit log for all actions"""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    tenant_id = Column(String, nullable=False, index=True)
    actor_id = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)

    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False, index=True)

    metadata = Column(JSON, nullable=True)
    result = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_id})>"


class IdempotencyCache(Base):
    """Idempotency key cache for replay protection"""

    __tablename__ = "idempotency_cache"

    idempotency_key = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    response_json = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<IdempotencyCache(key={self.idempotency_key})>"
