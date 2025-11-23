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

    audit_metadata = Column("metadata", JSON, nullable=True)  # Renamed to avoid SQLAlchemy reserved word
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


class Export(Base):
    """Export packages for evidence delivery"""

    __tablename__ = "exports"

    # Primary identifiers
    export_id = Column(String, primary_key=True)
    application_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Export configuration
    format = Column(String, nullable=False, default="zip")
    include_metadata = Column(Boolean, nullable=False, default=True)
    sign_package = Column(Boolean, nullable=False, default=True)

    # Export status
    status = Column(String, nullable=False, default="pending", index=True)  # pending, processing, completed, failed
    file_count = Column(Integer, nullable=True)
    total_size_bytes = Column(Integer, nullable=True)

    # Storage
    storage_path = Column(String, nullable=True)  # Path to ZIP file in blob storage
    signature = Column(String, nullable=True)  # Digital signature of the manifest

    # Error handling
    error_message = Column(Text, nullable=True)

    # Audit
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    correlation_id = Column(String, nullable=False, index=True)

    __table_args__ = (
        Index("ix_exports_tenant_app", "tenant_id", "application_id"),
        Index("ix_exports_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Export(id={self.export_id}, app={self.application_id}, status={self.status})>"


class Application(Base):
    """Restaurant permit applications"""

    __tablename__ = "applications"

    # Primary identifiers
    application_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    applicant_id = Column(String, nullable=False, index=True)

    # Application details
    application_type = Column(String, nullable=False)
    business_name = Column(String, nullable=False)
    business_address = Column(String, nullable=False)

    # Status tracking
    status = Column(String, nullable=False, default="draft", index=True)  # draft, submitted, under_review, approved, rejected, conditional

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decided_at = Column(DateTime, nullable=True)

    # Latest evaluation snapshot
    latest_snapshot_id = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_applications_tenant_status", "tenant_id", "status"),
        Index("ix_applications_applicant", "applicant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.application_id}, business={self.business_name}, status={self.status})>"


class ApplicationFact(Base):
    """Facts submitted for applications (upsertable by fact_name)"""

    __tablename__ = "application_facts"

    # Primary identifiers
    fact_id = Column(String, primary_key=True)
    application_id = Column(String, nullable=False, index=True)

    # Fact details
    fact_name = Column(String, nullable=False)
    fact_value = Column(JSON, nullable=False)  # {value: ..., type: ...}
    fact_type = Column(String, nullable=False)  # string, number, boolean, date, etc.

    # Evidence linkage
    supporting_evidence_id = Column(String, nullable=True, index=True)

    # Extraction metadata
    extractor_id = Column(String, nullable=True)  # Which extractor produced this fact
    extraction_confidence = Column(Float, nullable=True)  # 0.0 - 1.0

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_facts_app_name", "application_id", "fact_name", unique=True),
        Index("ix_facts_evidence", "supporting_evidence_id"),
    )

    def __repr__(self) -> str:
        return f"<ApplicationFact(id={self.fact_id}, app={self.application_id}, name={self.fact_name})>"


class DecisionSnapshot(Base):
    """Immutable snapshots of decision state at evaluation time"""

    __tablename__ = "decision_snapshots"

    # Primary identifiers
    snapshot_id = Column(String, primary_key=True)
    application_id = Column(String, nullable=False, index=True)

    # Snapshot metadata
    snapshot_version = Column(Integer, nullable=False, default=1)
    trigger_type = Column(String, nullable=False)  # on_demand, auto_evaluate, manual_override
    trigger_metadata = Column(JSON, nullable=True)

    # Facts snapshot (immutable copy at evaluation time)
    facts_snapshot = Column(JSON, nullable=False)  # Complete facts state

    # Evaluation results
    rule_outcomes = Column(JSON, nullable=False)  # List of rule results
    overall_recommendation = Column(String, nullable=False)  # approved, rejected, conditional, insufficient_data

    # Cryptographic integrity
    snapshot_hash = Column(String, nullable=False)  # SHA-256 of canonical JSON
    signature = Column(String, nullable=True)  # Digital signature

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("ix_snapshots_app_created", "application_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<DecisionSnapshot(id={self.snapshot_id}, app={self.application_id}, recommendation={self.overall_recommendation})>"
