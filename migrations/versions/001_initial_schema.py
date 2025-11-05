"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-11-05 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create evidence table"""
    op.create_table(
        "evidence",
        sa.Column("evidence_id", sa.String(), nullable=False),
        sa.Column("application_id", sa.String(), nullable=False),
        sa.Column("evidence_type", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hash_device", sa.String(length=64), nullable=False),
        sa.Column("sha256_hash_server", sa.String(length=64), nullable=True),
        sa.Column("captured_at_device", sa.DateTime(), nullable=False),
        sa.Column("captured_at_server", sa.DateTime(), nullable=True),
        sa.Column("time_drift_seconds", sa.Float(), nullable=True),
        sa.Column("gps_latitude", sa.Float(), nullable=False),
        sa.Column("gps_longitude", sa.Float(), nullable=False),
        sa.Column("gps_accuracy_meters", sa.Float(), nullable=False),
        sa.Column("exif_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("uploader_role", sa.String(), nullable=False),
        sa.Column("storage_uri", sa.String(), nullable=True),
        sa.Column("integrity_passed", sa.Boolean(), nullable=False),
        sa.Column("integrity_issues", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("evidence_id"),
    )
    op.create_index(op.f("ix_evidence_evidence_id"), "evidence", ["evidence_id"], unique=False)
    op.create_index(
        op.f("ix_evidence_application_id"), "evidence", ["application_id"], unique=False
    )


def downgrade() -> None:
    """Drop evidence table"""
    op.drop_index(op.f("ix_evidence_application_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_evidence_id"), table_name="evidence")
    op.drop_table("evidence")
