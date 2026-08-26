"""client_daily_snapshot

Revision ID: 7c2f4a9e1d05
Revises: 33b181b3da1c
Create Date: 2026-08-26 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7c2f4a9e1d05'
down_revision: Union[str, Sequence[str], None] = '33b181b3da1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'client_daily_snapshot',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('aum', sa.Numeric(), nullable=True),
        sa.Column('allocation_json', postgresql.JSONB(), nullable=True),
        sa.Column('top_issuer_concentration', sa.Numeric(), nullable=True),
        sa.Column('liquidity_pct', sa.Numeric(), nullable=True),
        sa.Column('monthly_purchase_value', sa.Numeric(), nullable=True),
        sa.Column('monthly_sale_value', sa.Numeric(), nullable=True),
        sa.Column('health_score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        'ix_client_daily_snapshot_client_date', 'client_daily_snapshot', ['client_id', 'snapshot_date'],
    )


def downgrade() -> None:
    op.drop_index('ix_client_daily_snapshot_client_date', table_name='client_daily_snapshot')
    op.drop_table('client_daily_snapshot')
