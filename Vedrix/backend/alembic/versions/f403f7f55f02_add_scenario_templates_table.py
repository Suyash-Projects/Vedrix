"""add_scenario_templates_table

Revision ID: f403f7f55f02
Revises: e5e168a2216e
Create Date: 2026-05-06 21:46:37.716418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f403f7f55f02'
down_revision: Union[str, None] = 'e5e168a2216e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create scenario templates table for advanced task simulations
    op.create_table('scenario_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=True),  # 'coding', 'system_design', 'behavioral'
        sa.Column('difficulty_level', sa.Integer(), nullable=True),
        sa.Column('estimated_time', sa.Integer(), nullable=True),
        sa.Column('scenarios', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop scenario templates table
    op.drop_table('scenario_templates')
