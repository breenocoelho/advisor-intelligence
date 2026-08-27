"""resolution_note em alert/insight + campos de cadastro em client

Revision ID: 9a1d4e6f2b3c
Revises: 7c2f4a9e1d05
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1d4e6f2b3c'
down_revision: Union[str, Sequence[str], None] = '7c2f4a9e1d05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('alerts', sa.Column('resolution_note', sa.Text(), nullable=True))
    op.add_column('insights', sa.Column('resolution_note', sa.Text(), nullable=True))

    op.add_column('clients', sa.Column('person_type', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('income_value', sa.Numeric(), nullable=True))
    op.add_column('clients', sa.Column('registration_updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'registration_updated_at')
    op.drop_column('clients', 'income_value')
    op.drop_column('clients', 'person_type')

    op.drop_column('insights', 'resolution_note')
    op.drop_column('alerts', 'resolution_note')
