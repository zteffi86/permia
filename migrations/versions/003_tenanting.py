"""Add tenanting and auth fields

Revision ID: 003
Revises: 002
Create Date: 2025-11-05 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tenant_id and make uploader_id required"""

    # Add tenant_id columns
    op.add_column(
        "evidence",
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="dev_tenant"),
    )
    op.add_column(
        "audit_log",
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="dev_tenant"),
    )
    op.add_column(
        "idempotency_cache",
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="dev_tenant"),
    )

    # Make uploader_id required
    op.alter_column("evidence", "uploader_id", nullable=False, server_default="dev_user")

    # Make audit_log actor fields required
    op.alter_column("audit_log", "actor_id", nullable=False, server_default="system")
    op.alter_column("audit_log", "actor_role", nullable=False, server_default="system")

    # Make mime_type_detected required
    op.alter_column(
        "evidence",
        "mime_type_detected",
        nullable=False,
        server_default="application/octet-stream",
    )

    # Add tenant indexes
    op.create_index("ix_evidence_tenant_id", "evidence", ["tenant_id"])
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index("ix_idempotency_cache_tenant_id", "idempotency_cache", ["tenant_id"])

    # Drop old index, add new composite
    op.drop_index("ix_evidence_application_id", "evidence")
    op.create_index("ix_evidence_tenant_app", "evidence", ["tenant_id", "application_id"])


def downgrade() -> None:
    """Remove tenant_id"""
    op.drop_index("ix_evidence_tenant_app", "evidence")
    op.create_index("ix_evidence_application_id", "evidence", ["application_id"])

    op.drop_index("ix_idempotency_cache_tenant_id", "idempotency_cache")
    op.drop_index("ix_audit_log_tenant_id", "audit_log")
    op.drop_index("ix_evidence_tenant_id", "evidence")

    op.drop_column("idempotency_cache", "tenant_id")
    op.drop_column("audit_log", "tenant_id")
    op.drop_column("evidence", "tenant_id")
