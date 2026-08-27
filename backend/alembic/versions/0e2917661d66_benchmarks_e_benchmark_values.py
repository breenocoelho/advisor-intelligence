"""benchmarks e benchmark_values

Revision ID: 0e2917661d66
Revises: d5a9c2e8f1b4
Create Date: 2026-08-27 16:53:46.941020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0e2917661d66'
down_revision: Union[str, Sequence[str], None] = 'd5a9c2e8f1b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'benchmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
    )
    op.create_table(
        'benchmark_values',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('benchmark_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('benchmarks.id'), nullable=False),
        sa.Column('value_date', sa.Date(), nullable=False),
        sa.Column('index_value', sa.Numeric(), nullable=False),
    )
    op.create_index('ix_benchmark_values_benchmark_id_date', 'benchmark_values', ['benchmark_id', 'value_date'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_benchmark_values_benchmark_id_date', table_name='benchmark_values')
    op.drop_table('benchmark_values')
    op.drop_table('benchmarks')
