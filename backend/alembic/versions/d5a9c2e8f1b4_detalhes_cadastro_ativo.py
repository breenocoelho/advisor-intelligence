"""mais detalhes de cadastro em assets (gestora, yield, liquidez, etc)

Revision ID: d5a9c2e8f1b4
Revises: c4f8b1d3e7a2
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a9c2e8f1b4'
down_revision: Union[str, Sequence[str], None] = 'c4f8b1d3e7a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('assets', sa.Column('manager_name', sa.String(), nullable=True))
    op.add_column('assets', sa.Column('payment_frequency', sa.String(), nullable=True))
    op.add_column('assets', sa.Column('liquidity_days', sa.Numeric(), nullable=True))
    op.add_column('assets', sa.Column('minimum_investment', sa.Numeric(), nullable=True))
    op.add_column('assets', sa.Column('risk_rating', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('assets', 'risk_rating')
    op.drop_column('assets', 'minimum_investment')
    op.drop_column('assets', 'liquidity_days')
    op.drop_column('assets', 'payment_frequency')
    op.drop_column('assets', 'manager_name')
