"""audit log, field overrides, campos customizados

Revision ID: cd13497b6b52
Revises: 0e2917661d66
Create Date: 2026-08-27 17:15:18.923407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cd13497b6b52'
down_revision: Union[str, Sequence[str], None] = '0e2917661d66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=True),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_org_created', 'audit_logs', ['org_id', 'created_at'])

    op.create_table(
        'client_field_overrides',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('field_name', sa.String(), nullable=False),
        sa.Column('override_value', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('client_id', 'field_name', name='uq_client_field_override'),
    )

    op.create_table(
        'client_extended_field_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.UniqueConstraint('org_id', 'key', name='uq_extended_field_org_key'),
    )
    op.create_table(
        'client_extended_field_options',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('field_definition_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('client_extended_field_definitions.id'), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
    )
    op.create_table(
        'client_extended_field_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('option_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('client_extended_field_options.id'), nullable=False),
        sa.UniqueConstraint('client_id', 'option_id', name='uq_extended_field_assignment'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('client_extended_field_assignments')
    op.drop_table('client_extended_field_options')
    op.drop_table('client_extended_field_definitions')
    op.drop_table('client_field_overrides')
    op.drop_index('ix_audit_logs_org_created', table_name='audit_logs')
    op.drop_table('audit_logs')
