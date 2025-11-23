"""add applications, facts and snapshots tables

Revision ID: 005_add_applications_facts_snapshots
Revises: 004_add_exports_table
Create Date: 2025-11-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '005_add_applications_facts_snapshots'
down_revision = '004_add_exports_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create applications table
    op.create_table(
        'applications',
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('applicant_id', sa.String(), nullable=False),
        sa.Column('application_type', sa.String(), nullable=False),
        sa.Column('business_name', sa.String(), nullable=False),
        sa.Column('business_address', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('latest_snapshot_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('application_id')
    )

    # Create indexes for applications
    op.create_index('ix_applications_tenant_id', 'applications', ['tenant_id'])
    op.create_index('ix_applications_applicant_id', 'applications', ['applicant_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])
    op.create_index('ix_applications_created_at', 'applications', ['created_at'])
    op.create_index('ix_applications_tenant_status', 'applications', ['tenant_id', 'status'])
    op.create_index('ix_applications_applicant', 'applications', ['applicant_id', 'created_at'])

    # Create application_facts table
    op.create_table(
        'application_facts',
        sa.Column('fact_id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('fact_name', sa.String(), nullable=False),
        sa.Column('fact_value', sa.JSON(), nullable=False),
        sa.Column('fact_type', sa.String(), nullable=False),
        sa.Column('supporting_evidence_id', sa.String(), nullable=True),
        sa.Column('extractor_id', sa.String(), nullable=True),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('fact_id')
    )

    # Create indexes for application_facts
    op.create_index('ix_facts_application_id', 'application_facts', ['application_id'])
    op.create_index('ix_facts_supporting_evidence_id', 'application_facts', ['supporting_evidence_id'])
    op.create_index('ix_facts_app_name', 'application_facts', ['application_id', 'fact_name'], unique=True)
    op.create_index('ix_facts_evidence', 'application_facts', ['supporting_evidence_id'])

    # Create decision_snapshots table
    op.create_table(
        'decision_snapshots',
        sa.Column('snapshot_id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('snapshot_version', sa.Integer(), nullable=False),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('trigger_metadata', sa.JSON(), nullable=True),
        sa.Column('facts_snapshot', sa.JSON(), nullable=False),
        sa.Column('rule_outcomes', sa.JSON(), nullable=False),
        sa.Column('overall_recommendation', sa.String(), nullable=False),
        sa.Column('snapshot_hash', sa.String(), nullable=False),
        sa.Column('signature', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('snapshot_id')
    )

    # Create indexes for decision_snapshots
    op.create_index('ix_snapshots_application_id', 'decision_snapshots', ['application_id'])
    op.create_index('ix_snapshots_created_at', 'decision_snapshots', ['created_at'])
    op.create_index('ix_snapshots_app_created', 'decision_snapshots', ['application_id', 'created_at'])


def downgrade() -> None:
    # Drop decision_snapshots table and indexes
    op.drop_index('ix_snapshots_app_created', table_name='decision_snapshots')
    op.drop_index('ix_snapshots_created_at', table_name='decision_snapshots')
    op.drop_index('ix_snapshots_application_id', table_name='decision_snapshots')
    op.drop_table('decision_snapshots')

    # Drop application_facts table and indexes
    op.drop_index('ix_facts_evidence', table_name='application_facts')
    op.drop_index('ix_facts_app_name', table_name='application_facts')
    op.drop_index('ix_facts_supporting_evidence_id', table_name='application_facts')
    op.drop_index('ix_facts_application_id', table_name='application_facts')
    op.drop_table('application_facts')

    # Drop applications table and indexes
    op.drop_index('ix_applications_applicant', table_name='applications')
    op.drop_index('ix_applications_tenant_status', table_name='applications')
    op.drop_index('ix_applications_created_at', table_name='applications')
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_applicant_id', table_name='applications')
    op.drop_index('ix_applications_tenant_id', table_name='applications')
    op.drop_table('applications')
