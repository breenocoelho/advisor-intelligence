"""advisor_daily_snapshot e client_interactions

Revision ID: c4f8b1d3e7a2
Revises: b3e7f0a2c9d1
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c4f8b1d3e7a2'
down_revision: Union[str, Sequence[str], None] = 'b3e7f0a2c9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'advisor_daily_snapshot',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('advisor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('advisors.id'), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('aum', sa.Numeric(), nullable=True),
        sa.Column('client_count', sa.Integer(), nullable=True),
        sa.Column('net_flow', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        'ix_advisor_daily_snapshot_advisor_date', 'advisor_daily_snapshot', ['advisor_id', 'snapshot_date'],
    )

    op.create_table(
        'client_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('advisor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('advisors.id'), nullable=True),
        sa.Column('interaction_type', sa.String(), nullable=False),
        sa.Column('interaction_date', sa.Date(), nullable=False),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        'ix_client_interactions_client_date', 'client_interactions', ['client_id', 'interaction_date'],
    )


def downgrade() -> None:
    op.drop_index('ix_client_interactions_client_date', table_name='client_interactions')
    op.drop_table('client_interactions')
    op.drop_index('ix_advisor_daily_snapshot_advisor_date', table_name='advisor_daily_snapshot')
    op.drop_table('advisor_daily_snapshot')
