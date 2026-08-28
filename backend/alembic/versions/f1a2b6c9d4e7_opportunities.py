"""opportunities

Revision ID: f1a2b6c9d4e7
Revises: cd13497b6b52
Create Date: 2026-08-27 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1a2b6c9d4e7'
down_revision: Union[str, Sequence[str], None] = 'cd13497b6b52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'opportunities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('source_alert_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alerts.id'), nullable=True),
        sa.Column('opportunity_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='detected'),
        sa.Column('potential_value', sa.Numeric(), nullable=True),
        sa.Column('urgency', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('client_id', 'opportunity_type', name='uq_opportunity_client_type'),
    )
    op.create_index('ix_opportunities_org_status', 'opportunities', ['org_id', 'status'])

    # coluna ja existia sem FK (comentario no model: "FK a adicionar quando
    # 'opportunities' existir") -- agora existe, fecha o CHECK de origem da Task
    op.create_foreign_key(
        'fk_tasks_opportunity_id', 'tasks', 'opportunities', ['opportunity_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_tasks_opportunity_id', 'tasks', type_='foreignkey')
    op.drop_index('ix_opportunities_org_status', table_name='opportunities')
    op.drop_table('opportunities')
