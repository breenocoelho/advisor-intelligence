"""thresholds, insights, tasks polimorfico

Revision ID: 33b181b3da1c
Revises: a5ea3e27a593
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '33b181b3da1c'
down_revision: Union[str, Sequence[str], None] = 'a5ea3e27a593'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'threshold_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('signal_key', sa.String(), nullable=False),
        sa.Column('suitability_profile', sa.String(), nullable=True),
        sa.Column('value', sa.Numeric(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_by', sa.String(), nullable=True),
    )

    op.create_table(
        'insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('insight_type', sa.String(), nullable=False),
        sa.Column('asset_class', sa.String(), nullable=True),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('evidence', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_insights_client_type_class', 'insights', ['client_id', 'insight_type', 'asset_class'])

    op.add_column('tasks', sa.Column('insight_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('insights.id'), nullable=True))
    op.add_column('tasks', sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_check_constraint(
        'chk_tasks_exactly_one_origin',
        'tasks',
        "(CASE WHEN alert_id IS NOT NULL THEN 1 ELSE 0 END) + "
        "(CASE WHEN insight_id IS NOT NULL THEN 1 ELSE 0 END) + "
        "(CASE WHEN opportunity_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
    )


def downgrade() -> None:
    op.drop_constraint('chk_tasks_exactly_one_origin', 'tasks', type_='check')
    op.drop_column('tasks', 'opportunity_id')
    op.drop_column('tasks', 'insight_id')
    op.drop_index('ix_insights_client_type_class', table_name='insights')
    op.drop_table('insights')
    op.drop_table('threshold_rules')
