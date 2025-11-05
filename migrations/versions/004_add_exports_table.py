"""add exports table

Revision ID: 004_add_exports_table
Revises: 003_tenanting
Create Date: 2025-11-05 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '004_add_exports_table'
down_revision = '003_tenanting'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create exports table
    op.create_table(
        'exports',
        sa.Column('export_id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('format', sa.String(), nullable=False),
        sa.Column('include_metadata', sa.Boolean(), nullable=False),
        sa.Column('sign_package', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('file_count', sa.Integer(), nullable=True),
        sa.Column('total_size_bytes', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.String(), nullable=True),
        sa.Column('signature', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('correlation_id', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('export_id')
    )

    # Create indexes for efficient queries
    op.create_index('ix_exports_application_id', 'exports', ['application_id'])
    op.create_index('ix_exports_tenant_id', 'exports', ['tenant_id'])
    op.create_index('ix_exports_status', 'exports', ['status'])
    op.create_index('ix_exports_created_at', 'exports', ['created_at'])
    op.create_index('ix_exports_expires_at', 'exports', ['expires_at'])
    op.create_index('ix_exports_correlation_id', 'exports', ['correlation_id'])

    # Composite indexes for common query patterns
    op.create_index('ix_exports_tenant_app', 'exports', ['tenant_id', 'application_id'])
    op.create_index('ix_exports_status_created', 'exports', ['status', 'created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_exports_status_created', table_name='exports')
    op.drop_index('ix_exports_tenant_app', table_name='exports')
    op.drop_index('ix_exports_correlation_id', table_name='exports')
    op.drop_index('ix_exports_expires_at', table_name='exports')
    op.drop_index('ix_exports_created_at', table_name='exports')
    op.drop_index('ix_exports_status', table_name='exports')
    op.drop_index('ix_exports_tenant_id', table_name='exports')
    op.drop_index('ix_exports_application_id', table_name='exports')

    # Drop table
    op.drop_table('exports')
