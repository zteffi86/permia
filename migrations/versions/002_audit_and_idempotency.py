"""Add audit log and idempotency cache

Revision ID: 002
Revises: 001
Create Date: 2025-11-05 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_log and idempotency_cache tables"""

    # Audit log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("correlation_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("actor_role", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("result", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_correlation_id", "audit_log", ["correlation_id"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_resource_id", "audit_log", ["resource_id"])

    # Idempotency cache
    op.create_table(
        "idempotency_cache",
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_key"),
    )
    op.create_index("ix_idempotency_cache_created_at", "idempotency_cache", ["created_at"])

    # Update evidence table with new columns
    op.add_column("evidence", sa.Column("mime_type_detected", sa.String(), nullable=True))
    op.add_column(
        "evidence",
        sa.Column("exif_present", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("evidence", sa.Column("exif_gps_latitude", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("exif_gps_longitude", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("exif_datetime", sa.DateTime(), nullable=True))
    op.add_column("evidence", sa.Column("uploader_id", sa.String(), nullable=True))
    op.add_column(
        "evidence",
        sa.Column("correlation_id", sa.String(), nullable=False, server_default="unknown"),
    )

    # Alter evidence.sha256_hash_server to NOT NULL
    op.alter_column("evidence", "sha256_hash_server", nullable=False)
    op.alter_column("evidence", "captured_at_server", nullable=False)
    op.alter_column("evidence", "time_drift_seconds", nullable=False)

    # Change storage_uri to storage_path
    op.alter_column("evidence", "storage_uri", new_column_name="storage_path")
    op.alter_column("evidence", "storage_path", nullable=False)

    # Add indexes
    op.create_index("ix_evidence_correlation_id", "evidence", ["correlation_id"])


def downgrade() -> None:
    """Drop audit_log and idempotency_cache tables"""
    op.drop_index("ix_evidence_correlation_id", "evidence")
    op.alter_column("evidence", "storage_path", new_column_name="storage_uri")
    op.drop_column("evidence", "correlation_id")
    op.drop_column("evidence", "uploader_id")
    op.drop_column("evidence", "exif_datetime")
    op.drop_column("evidence", "exif_gps_longitude")
    op.drop_column("evidence", "exif_gps_latitude")
    op.drop_column("evidence", "exif_present")
    op.drop_column("evidence", "mime_type_detected")

    op.drop_index("ix_idempotency_cache_created_at", "idempotency_cache")
    op.drop_table("idempotency_cache")

    op.drop_index("ix_audit_log_resource_id", "audit_log")
    op.drop_index("ix_audit_log_timestamp", "audit_log")
    op.drop_index("ix_audit_log_correlation_id", "audit_log")
    op.drop_table("audit_log")
