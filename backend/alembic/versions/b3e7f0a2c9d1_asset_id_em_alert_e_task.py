"""asset_id em alert e task

Revision ID: b3e7f0a2c9d1
Revises: 9a1d4e6f2b3c
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b3e7f0a2c9d1'
down_revision: Union[str, Sequence[str], None] = '9a1d4e6f2b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('alerts', sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id'), nullable=True))
    op.add_column('tasks', sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'asset_id')
    op.drop_column('alerts', 'asset_id')
